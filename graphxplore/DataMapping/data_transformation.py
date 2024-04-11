import collections
import contextlib
from typing import Union, Optional, Dict, List, Tuple
from graphxplore.MetaDataHandling import MetaData
from .meta_lattice import MetaLattice
from .data_mapping import DataMapping, VariableMapping, TableMapping
from .data_structure_transformer import (CSVDataFlattener, DataSegmentor, SourceDataType, FlattenerLatticeConfig,
                                         TableMappingType, SourceDataLine)

class PrimaryKeyGenerator:
    def __init__(self, table_mapping: TableMapping, source_meta: MetaData, mapping_type: TableMappingType):
        if mapping_type != table_mapping.type:
            raise AttributeError('Primary key generator initialized with from table mapping type')
        for table in table_mapping.source_tables:
            if table not in source_meta.get_table_names():
                raise AttributeError('Source table "' + table + '" of table mapping not specified in source metadata')
        self.table_mapping = table_mapping
        self.source_meta = source_meta

    def generate_primary_key(self, source_data: SourceDataLine) -> Optional[str]:
        raise NotImplemented('Never call parent class')

    @staticmethod
    def from_table_mapping(table_mapping: TableMapping, source_meta: MetaData) -> 'PrimaryKeyGenerator':
        if table_mapping.type == TableMappingType.OneToOne:
            return OneToOnePrimaryKeyGenerator(table_mapping, source_meta)
        elif table_mapping.type == TableMappingType.Inherited:
            return InheritedPrimaryKeyGenerator(table_mapping, source_meta)
        elif table_mapping.type == TableMappingType.Merge:
            return MergePrimaryKeyGenerator(table_mapping, source_meta)
        elif table_mapping.type == TableMappingType.Concatenate:
            return ConcatenatePrimaryKeyGenerator(table_mapping, source_meta)
        else:
            raise NotImplemented('Table mapping type not implemented for primary key generator')

class OneToOnePrimaryKeyGenerator(PrimaryKeyGenerator):
    def __init__(self, table_mapping: TableMapping, source_meta: MetaData):
        super().__init__(table_mapping, source_meta, TableMappingType.OneToOne)
        self.table_to_copy = self.table_mapping.source_tables[0]
        self.pk_to_copy = self.source_meta.get_primary_key(self.table_to_copy)

    def generate_primary_key(self, source_data: SourceDataLine) -> str:
        return str(source_data.get_singular_value(self.table_to_copy, self.pk_to_copy))

class InheritedPrimaryKeyGenerator(PrimaryKeyGenerator):
    def __init__(self, table_mapping: TableMapping, source_meta: MetaData):
        super().__init__(table_mapping, source_meta, TableMappingType.Inherited)

    def generate_primary_key(self, source_data: SourceDataLine) -> Optional[str]:
        return None

class MergePrimaryKeyGenerator(PrimaryKeyGenerator):
    def __init__(self, table_mapping: TableMapping, source_meta: MetaData):
        super().__init__(table_mapping, source_meta, TableMappingType.Merge)
        self.table_pk_map = {table : self.source_meta.get_primary_key(table) for table in table_mapping.source_tables}

    def generate_primary_key(self, source_data: SourceDataLine) -> str:
        merged_returns = collections.defaultdict(list)
        for table, pk in self.table_pk_map.items():
            pk_val = source_data.get_singular_value(table, pk)
            if pk_val is not None:
                merged_returns[str(pk_val)].append(table)

        if len(merged_returns) == 0:
            raise AttributeError('No valid primary key value to merge found in unit of source data for source tables "'
                                 + '", '.join(self.table_mapping.source_tables) + '"')

        if len(merged_returns) > 1:
            raise AttributeError('Multiple differing primary key values for merging found in unit of source data: "'
                                 + '", '"".join((pk_val + '" in table(s) ("' + '", "'.join(tables) + '")'
                                                 for pk_val, tables in merged_returns.items())))
        return list(merged_returns.keys())[0]

class ConcatenatePrimaryKeyGenerator(PrimaryKeyGenerator):
    def __init__(self, table_mapping: TableMapping, source_meta: MetaData):
        super().__init__(table_mapping, source_meta, TableMappingType.Concatenate)
        self.uid = -1

    def generate_primary_key(self, source_data: SourceDataLine) -> str:
        self.uid += 1
        return str(self.uid)


class DataTransformation:
    """This class conducts the ETL process of transforming the given source dataset to the specified target dataset
    using the given :class:`DataMapping`

    :param data_mapping: The variable mappings
    """
    def __init__(self, data_mapping : DataMapping):
        """Constructor method
        """
        self.data_mapping = data_mapping
        self.inheriting_tables = {table : table_mapping.to_inherit
                                  for table, table_mapping in self.data_mapping.table_mappings.items()
                                  if table_mapping.type == TableMappingType.Inherited}
        self.assigned_tables = {table for table in self.data_mapping.target.get_table_names()
                                if table not in self.inheriting_tables}


    def transform_to_target(self, source_type : SourceDataType,
                            source_specifier : Union[str, Dict[str, List[Dict[str, str]]]],
                            data_target : Union[str, Dict[str, List[Dict[str, str]]]],
                            global_unique_target_keys : bool = False, source_file_encoding : Optional[str] = None) -> None:
        """Reads the source data from a directory with CSV files or from a Neo4J database. Transforms the data and
        writes it to a target directory as CSV files.

        :param source_type: The type of source data
        :param source_specifier: Either a source directory path, the name of the Neo4J database or a dictionary
            containing the source data set
        :param data_target: The path to a directory where CSV files are written or a data dictionary where data is inserted
        :param global_unique_target_keys: If ``True``, the generated IDs are unique across all
            automatically generated primary keys, defaults to ``False``
        :param source_file_encoding: Specifies the file encoding of all source tables, if read from a CSV. Will be
            detected if not specified, defaults to ``None``
        """
        with DataSegmentor(self.data_mapping.target, self.data_mapping.target_lattice, self.inheriting_tables,
                           data_target, global_unique_target_keys) as segmentor:
            for target_table in self.assigned_tables:
                print('Start generating data for target table "'+ target_table + '"')
                table_mapping = self.data_mapping.table_mappings[target_table]
                sub_target_lattice, flattener_config, lattice_mappings\
                    = self.__get_transformation_data_for_target_table(target_table)
                key_generator = PrimaryKeyGenerator.from_table_mapping(table_mapping, self.data_mapping.source)
                with contextlib.ExitStack() as inner_stack:
                    if source_type == SourceDataType.CSV:
                        flattener = inner_stack.enter_context(CSVDataFlattener(self.data_mapping.source, source_specifier,
                                                                               table_mapping.type, flattener_config,
                                                                               source_file_encoding))
                    elif source_type == SourceDataType.Database:
                        raise NotImplemented('Not implemented')
                    else:
                        raise NotImplemented('Not implemented')

                    counter = 0
                    pk = self.data_mapping.target.get_primary_key(target_table)
                    for source_line in flattener:
                        counter += 1
                        if counter % 100000 == 0:
                            print('Transformed ' + str(counter) + ' source lines to target format')
                        # skip whole source data unit, if condition of table mapping is not met
                        if not table_mapping.condition.valid(source_line):
                            continue
                        target_line = collections.defaultdict(dict)
                        target_line[target_table][pk] = key_generator.generate_primary_key(source_line)
                        for mapping in lattice_mappings:
                            target_line[mapping.target_table][mapping.target_variable] = mapping[source_line]
                        segmentor.write_row(sub_target_lattice, target_line)

    def __get_transformation_data_for_target_table(self, target_table : str)\
            -> Tuple[MetaLattice, FlattenerLatticeConfig, List[VariableMapping]]:
        """Generates the :class:`MetaLattice` objects for the relevant source and target tables (and their
        primary/foreign key relations) to map all data for the specified ``target_table``.
        All necessary :class:`VariableMapping` objects and required source tables/variables are identified as well and
        split into data required for singular sources and data aggregation (if aggregation required).

        :param target_table: The name of the target table
        :return: Returns a quadruple of all generated data
        """
        if target_table not in self.assigned_tables:
            raise AttributeError('Target table "' + target_table
                                 + '" cannot be the starting point for a transformation, because its relation to the '
                                   'source dataset is inherited')
        # get sub lattice with other inheriting tables
        sub_target_lattice = self.data_mapping.target_lattice.get_sub_lattice_from_inheritance(
            target_table, self.inheriting_tables)
        required_singular_source_vars = collections.defaultdict(set)
        required_aggregated_source_vars = collections.defaultdict(lambda : collections.defaultdict(set))
        lattice_mappings = []
        for table in sub_target_lattice.children.keys():
            for variable in self.data_mapping.target.get_variable_names(table):
                if self.data_mapping.variable_should_get_mapped(table, variable):
                    var_mapping = self.data_mapping.get_variable_mapping(table, variable)
                    lattice_mappings.append(var_mapping)
                    for source_table, source_vars in var_mapping.sources.items():
                        for source_var, aggregator_info in source_vars:
                            if aggregator_info is None:
                                required_singular_source_vars[source_table].add(source_var)
                            else:
                                required_aggregated_source_vars[source_table][source_var].add(aggregator_info)
        table_mapping = self.data_mapping.table_mappings[target_table]
        for source_table, source_vars in table_mapping.condition.get_required_data().items():
            for source_var, aggregator_info in source_vars:
                if aggregator_info is None:
                    required_singular_source_vars[source_table].add(source_var)
                else:
                    required_aggregated_source_vars[source_table][source_var].add(aggregator_info)

        sub_source_upward_lattice = self.data_mapping.source_lattice.get_sub_lattice_whitelist(
            table_mapping.source_tables, required_singular_source_vars.keys())

        # caveat: Each source table is checked for multi reference independently. When source tables are merged, this
        # can still lead to multi reference by different source tables. The user has to check that the same primary key
        # values from distinct tables always reference the same foreign key values
        for source_table in table_mapping.source_tables:
            if sub_source_upward_lattice.has_multi_reference_relative(source_table):
                raise AttributeError('Source table "' + source_table +
                                     '" has multi referenced descendent table. This prevents data flattening')

        lattice_config = FlattenerLatticeConfig(sub_source_upward_lattice, required_singular_source_vars)

        if len(required_aggregated_source_vars) > 0:
            sub_source_downward_lattice  = self.data_mapping.source_lattice.get_ancestor_lattice(
                table_mapping.source_tables, required_aggregated_source_vars.keys())
            for source_table in table_mapping.source_tables:
                if sub_source_downward_lattice.has_multi_reference_relative(source_table, upward=False):
                    raise AttributeError('Source table "' + source_table +
                                         '" has multi referenced ancestor table. This prevents data aggregation')
            lattice_config.aggregation_lattice = sub_source_downward_lattice
            lattice_config.required_aggregation_vars = required_aggregated_source_vars

        return sub_target_lattice, lattice_config, lattice_mappings