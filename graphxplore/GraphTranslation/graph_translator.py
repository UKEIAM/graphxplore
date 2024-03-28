import time
import collections
import os
import csv
import contextlib
from typing import Iterable, Union, Optional, Tuple, Dict
from graphxplore.MetaDataHandling import MetaData, VariableInfo, VariableType
from graphxplore.Basis import (GraphCSVWriter, GraphType, BaseUtils, GraphDatabaseWriter, GraphOutputType,
                               GraphDatabaseUtils, RelationalDataIODevice)
from graphxplore.Basis.BaseGraph import BinBoundInfo, BaseLabels, BaseNode, BaseEdge, BaseEdgeType, BaseNodeType

class GraphTranslator:
    """This class transforms relational data represented by one or multiple CSVs to a graph structure given a
    :class:`~graphxplore.MetaDataHandling.MetaData` object. Each unique triplet of table, variable and cell is assigned
    to a node in the graph structure. Cell nodes are connected to the node for their primary key value via an edge.
    This way, multiple primary keys with some identical cell value share a neighbor and are connected if they are in a
    foreign key relation. As a result, efficient data lookup can be achieved while avoiding complex joins across
    different tables. The generated :class:`~graphxplore.Basis.BaseGraph.BaseGraph` forms the basis for all further
    data exploration/analysis methods.

    :param metadata: The metadata of the relational dataset
    :param missing_vals: This cell values are skipped and not added to the generated graph. Convenient for data with
        missing values, defaults to common missing value definitions
    :param file_encoding: The file encoding of the CSV files (ascii, utf-8,...) in chardet definition.
        Is guessed if not specified, defaults to None
    """
    def __init__(self, metadata: MetaData,
                 missing_vals : Iterable[Union[str, None]] = (None, '', 'NaN', 'Na', 'NA', 'NAN', 'nan', 'na'),
                 file_encoding : Optional[str] = None):
        """Constructor method
        """
        self.metadata = metadata
        self.missing_vals = set(missing_vals)
        self.table_look_data = collections.defaultdict(dict)
        self.node_uuid = 0
        self.edge_uuid = 0
        self.table_names = self.metadata.get_table_names()
        self.primary_key_link = dict([(table, False) for table in self.table_names])
        self.line_counter = 0
        self.writer = None
        self.file_encoding = file_encoding

    def transform_to_graph(self, csv_data: Union[str, Dict[str, Iterable[Dict[str, str]]]], output: str,
                           output_type : GraphOutputType = GraphOutputType.CSV, overwrite: bool = False,
                           address : str = GraphDatabaseUtils.get_neo4j_address(),
                           auth: Tuple[str, str] = ("neo4j", "")) -> None:
        """Reads all CSV files from a data directory, that are specified in the supplied metadata. Generates a graph
        with nodes for primary keys and attributes. Links between primary keys, if they appear in a primary/foreign key
        relation between different CSV files. Stores the generated graph in the specified output directory as CSV files
        or in a Neo4j database.

        :param csv_data: The input data of the CSV files either as directory path containing the CSV files or as
            dictionary of table name and table data as dictionary per row
        :param output: The output directory for the generated graph, will be written as CSV files or the name of the
            Neo4j database
        :param output_type: The type of output. Either CSV or a Neo4j database, defaults to CSV
        :param overwrite: If written to an existing Neo4j database, overwriting has to be set here
        :param address: The address of the Neo4J DBMS. Can be generated with
            :func:`~graphxplore.Basis.GraphDatabaseUtils.get_neo4j_address()`. Will only be used if the graph should be
            written to database
        :param auth: username and password to access the Neo4j DBMS. Will only be used if graph should be written to
            database
        """
        print('Start building graph')

        start_time = time.time()

        self.__initialize_look_up()

        with contextlib.ExitStack() as stack:
            if output_type == GraphOutputType.CSV:
                self.writer = stack.enter_context(GraphCSVWriter(output, GraphType.Base))
            else:
                self.writer = stack.enter_context(GraphDatabaseWriter(GraphType.Base, output, overwrite, address, auth))

            for table in self.table_names:
                table_label = self.metadata.get_label(table)
                if table_label == '':
                    table_label = table

                with RelationalDataIODevice(csv_data, table, file_encoding=self.file_encoding) as reader:

                    print('Processing table ' + table_label)

                    self.line_counter = 0
                    list(map(lambda row: self.__process_row(row, table), reader))

                    print('Binning attributes with large value range')

                    self.__generate_bins(table)

                    self.table_look_data[table]['stored_attributes'].clear()
                    self.table_look_data[table]['attributes_to_bin'].clear()

        end_time = time.time()
        print('Done, took ' + str(end_time-start_time) + ' seconds, generated ' + str(self.node_uuid) + ' nodes and '
              + str(self.edge_uuid) + ' edges')

    def __initialize_look_up(self) -> None:
        """Initialize data structures for storage of generated nodes. Attribute nodes are deleted, after the table was
        fully processed. Primary key nodes are deleted, if the primary keys are not used as foreign keys in other
        tables.
        """
        for table in self.table_names:
            self.table_look_data[table]['stored_keys'] = collections.defaultdict(int)
            self.table_look_data[table]['stored_attributes'] = collections.defaultdict(int)
            self.table_look_data[table]['attributes_to_bin'] = collections.defaultdict(lambda
                                                                                       : collections.defaultdict(int))
            for foreign_key, foreign_table in self.metadata.get_foreign_keys(table).items():
                self.primary_key_link[foreign_table] = True

    def __process_row(self, row: dict, table: str) -> None:
        """Reads one row from the CSV and generates a node for each column. The node is labeled as 'Key' if it is a
        primary or foreign key and as 'Attribute' if it is no key. Additionally, the table of origin is added as label
        to all nodes. Edges between the generated nodes are added. The generated nodes are checked for uniqueness to
        conclude nodes with the same value.

        :param row: The row of the CSV
        :param table: The name of the CSV
        """
        primary_key = self.metadata.get_primary_key(table)
        table_label = self.metadata.get_label(table)
        if table_label == '':
            table_label = table
        variable_names = self.metadata.get_variable_names(table)
        foreign_key_references = self.metadata.get_foreign_keys(table)
        store_keys = self.primary_key_link[table]
        # generate node for data point/primary key
        prim_info = self.metadata.get_variable(table, primary_key)
        data_point_id = self.__generate_and_insert_node(row[primary_key], table, table_label, primary_key, prim_info,
                                                        store_keys)
        # primary key column should never contain empty cells
        if data_point_id == -1:
            raise AttributeError('In table "' + table + '" primary key column "' + primary_key
                                 + '" contains empty cells')

        # connect data point to attributes in relevant_columns (no foreign keys)
        for variable in variable_names:
            var_info = self.metadata.get_variable(table, variable)
            if var_info.variable_type != VariableType.Categorical and var_info.variable_type != VariableType.Metric:
                continue

            attribute_id = self.__generate_and_insert_node(row[variable], table, table_label, variable, var_info, True)
            # attribute cell is empty or invalid
            if attribute_id == -1:
                continue
            self.edge_uuid += 1
            self.writer.write_edge(BaseEdge(data_point_id, attribute_id, BaseEdgeType.HAS_ATTR_VAL))

        # connect data point to foreign key entries
        for foreign_key, foreign_table in foreign_key_references.items():
            foreign_label = self.metadata.get_label(foreign_table)
            if foreign_label == '':
                foreign_label = foreign_table
            foreign_key_info = self.metadata.get_variable(foreign_table, foreign_key)
            foreign_key_id = self.__generate_and_insert_node(row[foreign_key], foreign_table, foreign_label,
                                                             foreign_key, foreign_key_info, True)
            # no foreign key linked
            if foreign_key_id == -1:
                continue

            self.edge_uuid += 1
            self.writer.write_edge(BaseEdge(foreign_key_id, data_point_id, BaseEdgeType.CONNECTED_TO))

        self.line_counter += 1
        if self.line_counter % 1000000 == 0:
            print('Processed ' + str(self.line_counter) + ' lines')

    def __generate_bins(self, table: str) -> None:
        """Generates bins for all attributes assigned for binning using quintiles. Values in the first quintile are
        assigned to the 'low' bin, values in the second to fourth quintile are assigned to the 'normal' bin and
        values in the fifth quintile to the 'high' bin. For each bin a new node is created that has an edge to all
        nodes representing the values within the bin.

        :param table: The table for which attributes are binned
        """
        generated_bins = {}
        # derive bins
        for attribute, values in self.table_look_data[table]['attributes_to_bin'].items():
            var_info = self.metadata.get_variable(table, attribute)
            if var_info.binning.ref_low is not None:
                low = var_info.binning.ref_low
                high = var_info.binning.ref_high
            else:
                sorted_vals = sorted(values.items())
                low = float(BaseUtils.calculate_quartile_quintile_sorted_dist(sorted_vals, False, 1))
                high = float(BaseUtils.calculate_quartile_quintile_sorted_dist(sorted_vals, False, 4))
            generated_bins[attribute] = {'lower': low, 'upper': high, 'info' : var_info}

        assigned_bins = collections.defaultdict(lambda : collections.defaultdict(list))

        # assign nodes to bins
        for node, node_id in self.table_look_data[table]['stored_attributes'].items():
            if node.name not in generated_bins:
                continue

            lower = generated_bins[node.name]['lower']
            upper = generated_bins[node.name]['upper']
            info = generated_bins[node.name]['info']
            if info.binning.exclude_from_binning is not None and node.val in info.binning.exclude_from_binning:
                continue
            bins = assigned_bins[node.name]
            (bins['low'] if node.val < lower else bins['high'] if node.val > upper else bins['normal']).append(node_id)

        table_label = self.metadata.get_label(table)
        if table_label == '':
            table_label = table

        # generate bin nodes and edges and write to output
        for attribute, bins in assigned_bins.items():
            ref_lower = generated_bins[attribute]['lower']
            ref_upper = generated_bins[attribute]['upper']
            info = generated_bins[attribute]['info']
            for bin_val, binned_nodes in bins.items():
                self.node_uuid += 1
                bin_id = self.node_uuid
                labels = BaseLabels(membership_labels=tuple([table_label] + info.labels),
                                    node_type=BaseNodeType.AttributeBin)
                bin_name = attribute
                desc = info.description
                node = BaseNode(bin_id, labels, bin_name, bin_val, desc,
                                BinBoundInfo(ref_lower, ref_upper))
                self.writer.write_node(node)
                for binned_node in binned_nodes:
                    self.writer.write_edge(BaseEdge(source=binned_node, target=bin_id,
                                                    edge_type=BaseEdgeType.ASSIGNED_BIN))


    def __generate_and_insert_node(self, value: str, table: str, table_label: str, var_name: str,
                                   var_info : VariableInfo, insert_in_map: bool) -> int:
        """Generates a Node object from the specified data with 'Key' or 'Attribute' and the table name as labels.
        The node has to two properties: the column name as 'name' and the cell value as 'value'. The generated node is
        checked, if it already exists (if 'insert_in_map' is set). The existing or newly generated id of the node is
        returned.

        :param value: The cell value as string
        :param table: The CSV file
        :param table_label: The label of the CSV file
        :param var_name: The name of the column
        :param var_info: Variable information containing metadata for the variable
        :param insert_in_map: If true the node is checked for uniqueness (not necessary for primary keys)
        :return: Returns the id of the generated node
        """
        if value in self.missing_vals or (var_info.artifacts is not None and value in var_info.artifacts):
            if var_info.default_value is None:
                return -1
            value = var_info.default_value
        cast_value = var_info.cast_value_to_data_type(value)
        # cell value does not belong to column data type
        if cast_value is None:
            return -1
        if var_info.variable_type == VariableType.PrimaryKey or var_info.variable_type == VariableType.ForeignKey:
            node_type = BaseNodeType.Key
        else:
            node_type = BaseNodeType.Attribute
        desc = var_info.description
        labels = BaseLabels(membership_labels = tuple([table_label] + var_info.labels), node_type = node_type)
        node = BaseNode(self.node_uuid + 1, labels, var_name, cast_value, desc)

        should_bin = node_type == BaseNodeType.Attribute and var_info.binning is not None and var_info.binning.should_bin

        if should_bin and var_info.binning.exclude_from_binning is not None:
            for entry in var_info.binning.exclude_from_binning:
                if entry == cast_value:
                    should_bin = False
                    break

        if node_type == BaseNodeType.Attribute or insert_in_map:
            if node_type == BaseNodeType.Key:
                node_id = self.__insert_into_lookup(node, self.table_look_data[table]['stored_keys'])
            else:
                node_id = self.__insert_into_lookup(node, self.table_look_data[table]['stored_attributes'])
                if should_bin:
                    self.table_look_data[table]['attributes_to_bin'][var_name][cast_value] += 1

        else :
            node_id = self.node_uuid + 1
        # write node if it was not generated before
        # primary keys are always unique and don't have to be added to lookup map
        # unless they are used as foreign keys
        if node_id == self.node_uuid + 1:
            self.node_uuid += 1
            self.writer.write_node(node)

        return node_id

    @staticmethod
    def __insert_into_lookup(node: BaseNode, lookup: dict) -> int:
        """Checks if the specified node already exists in the lookup structure.

        :param node: The generated node
        :param lookup: The lookup structure
        :return: Returns the existing or newly generated node ID
        """
        node_id = lookup[node]
        # node was not present before
        if node_id == 0:
            lookup[node] = node.node_id
            return node.node_id
        else:
            return node_id
