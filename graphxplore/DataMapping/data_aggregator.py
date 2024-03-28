import collections
import math
from enum import Enum
import copy
from typing import Union, Optional, Set, Tuple, Mapping, Iterable, Dict, List
from .meta_lattice import MetaLattice
from graphxplore.MetaDataHandling import DataType, MetaData, VariableInfo
from graphxplore.Basis import BaseUtils, RelationalDataIODevice

class AggregatorType(str, Enum):
    """The type of variable data aggregator.
    """
    List = 'LIST'
    Count = 'COUNT'
    Concatenate = 'CONCATENATE'
    Sum = 'SUM'
    Min = 'MIN'
    Max = 'MAX'
    Mean = 'MEAN'
    Std = 'STDEV'
    Median = 'MEDIAN'
    Amplitude = 'AMPLITUDE'

class DataAggregator:
    """This class gathers data of time series, events or other data associated with the same primary key value. To
    achieve this, a :class:`~graphxplore.DataMapping.MetaLattice` object is traversed in inverse order
    (starting from its maximal elements), and the table data is loaded and assigned to each unique primary key value.
    Data for variables in ``required_vars`` is aggregated with the specified :class:`AggregatorType` and
    :class:`~graphxplore.MetaDataHandling.DataType`.

    :param meta: The metadata of the whole dataset
    :param lattice: The lattice that will be traversed in inverse order.
    :param required_vars: The variables required for data aggregation per table
    """
    def __init__(self, meta: MetaData,  lattice : MetaLattice,
                 required_vars : Mapping[str, Mapping[str, Iterable[Tuple[AggregatorType, DataType]]]]):
        """Constructor method
        """
        self.meta = meta
        self.lattice = lattice
        self.required_vars = required_vars
        # start table -> primary key value -> AggregatedData
        self.aggregated_data = {table : {} for table in self.lattice.max_elements}

    def aggregate_data(self) -> None:
        """Starts the data aggregation and stores the results.
        """
        raise NotImplemented('Never call parent class')

class CSVDataAggregator(DataAggregator):
    """This class inherits from :class:`DataAggregator` and implements the process by reading data directly from the
    CSV files.

    :param data_source: The path to a directory with CSV files or a dictionary containing the source dataset
    :param meta: The metadata of the whole dataset
    :param lattice: The lattice that will be traversed in inverse order
    :param required_vars: The variables required for data aggregation per table
    :param file_encoding: Specifies the file encoding of all read CSV tables. Will be detected if not specified,
        defaults to None
    """
    def __init__(self, data_source : Union[str, Dict[str, List[Dict[str, str]]]], meta: MetaData,  lattice : MetaLattice,
                 required_vars : Mapping[str, Mapping[str, Iterable[Tuple[AggregatorType, DataType]]]],
                 file_encoding : Optional[str] = None):
        """Constructor method
        """
        super().__init__(meta, lattice, required_vars)
        RelationalDataIODevice.check_data_location(data_source)
        # if not os.path.isdir(source_dir):
        #     raise AttributeError(source_dir + ' was specified for data aggregation, but it is not a valid source '
        #                                       'directory')
        self.data_source = data_source
        # start table -> start primary key value -> ancestor table -> ancestor primary key values
        self.downward_key_relations = {table : collections.defaultdict(lambda: collections.defaultdict(list))
                                        for table in self.lattice.max_elements}
        # ancestor table -> ancestor primary key value -> start table -> start primary key value
        self.upward_key_relations = collections.defaultdict(lambda : collections.defaultdict(dict))
        self.file_encoding = file_encoding

    def aggregate_data(self) -> None:
        start_tables = self.lattice.max_elements
        visited = set(start_tables)
        queue = list(start_tables)
        while len(queue) > 0:
            current = queue.pop(0)
            self.__extract_data(current)
            for parent in self.lattice.parents[current]:
                if parent not in visited:
                    visited.add(parent)
                    queue.append(parent)

    def __extract_data(self, table : str):
        with RelationalDataIODevice(self.data_source, table, file_encoding=self.file_encoding) as reader:
            print('Loading data for aggregation from table "' + table + '"')
            is_start_table = table in self.lattice.max_elements
            primary_key = self.meta.get_primary_key(table)
            # start table -> start primary key val -> variable -> value -> count
            data_to_aggregate = collections.defaultdict(
                lambda: collections.defaultdict(
                    lambda: collections.defaultdict(
                        lambda : collections.defaultdict(int))))
            for line in reader:
                pk_value = line[primary_key]
                if is_start_table:
                    self.aggregated_data[table][pk_value] = AggregatedData()
                    continue
                self.__insert_key_relation(table, line)
                # add data for required variables
                if table not in self.required_vars:
                    continue
                for required_var in self.required_vars[table].keys():
                    val = line[required_var]
                    if val != '':
                        for start_table, start_pk_value in self.upward_key_relations[table][pk_value].items():
                            data_to_aggregate[start_table][start_pk_value][required_var][val] += 1
            # aggregate data
            if table in self.required_vars:
                for start_table in self.lattice.max_elements:
                    for pk_value, aggregated in self.aggregated_data[start_table].items():
                        for required_var, aggregation_infos in self.required_vars[table].items():
                            for agg_type, data_type in aggregation_infos:
                                if (start_table not in data_to_aggregate
                                        or pk_value not in data_to_aggregate[start_table]
                                        or required_var not in data_to_aggregate[start_table][pk_value]):
                                    agg_val = None
                                else:
                                    val_dist = data_to_aggregate[start_table][pk_value][required_var]
                                    agg_val = self.__calculate_aggregated_value(val_dist, agg_type, data_type)
                                aggregated.add_variable_aggregation(table, required_var, data_type, agg_type, agg_val)



    def __insert_key_relation(self, table : str, line : Dict[str, str]) -> None:
        pk_value = line[self.meta.get_primary_key(table)]
        for foreign_key, foreign_table in self.meta.get_foreign_keys(table).items():
            fk_value = line[foreign_key]
            if fk_value != '':
                if foreign_table in self.lattice.max_elements:
                    self.downward_key_relations[foreign_table][fk_value][table].append(pk_value)
                    self.upward_key_relations[table][pk_value][foreign_table] = fk_value
                else:
                    self.upward_key_relations[table][pk_value].update(
                        self.upward_key_relations[foreign_table][fk_value])
                    for start_table, start_pk_value in self.upward_key_relations[table][pk_value].items():
                        self.downward_key_relations[start_table][start_pk_value][table].append(pk_value)

    @staticmethod
    def __calculate_aggregated_value(val_dist : Dict[str, int], agg_type : AggregatorType,
                                     data_type : DataType) -> Optional[Union[str, int, float]]:
        casted_dist = {VariableInfo.cast_value(val, data_type): count
                       for val, count in val_dist.items()
                       if VariableInfo.cast_value(val, data_type) is not None
                       and not ((data_type == DataType.Integer
                                 or data_type == DataType.Decimal)
                                and math.isnan(float(val)))}
        if agg_type == AggregatorType.List:
            agg_val = set(casted_dist.keys())
        elif agg_type == AggregatorType.Count:
            agg_val = sum(casted_dist.values())
        elif agg_type == AggregatorType.Concatenate:
            agg_val = ';'.join(sorted(casted_dist.keys()))
        else:
            if len(casted_dist) == 0:
                agg_val = None
            elif agg_type == AggregatorType.Sum:
                agg_val = sum((val * count for val, count in casted_dist.items()))
            elif agg_type == AggregatorType.Min:
                agg_val = min(casted_dist.keys())
            elif agg_type == AggregatorType.Max:
                agg_val = max(casted_dist.keys())
            elif agg_type == AggregatorType.Mean:
                agg_val = BaseUtils.calculate_mean(casted_dist)
            elif agg_type == AggregatorType.Median:
                agg_val = BaseUtils.calculate_median(casted_dist)
            elif agg_type == AggregatorType.Std:
                agg_val = BaseUtils.calculate_std(casted_dist)
            elif agg_type == AggregatorType.Amplitude:
                agg_val = max(casted_dist.keys()) - min(casted_dist.keys())
            else:
                raise AttributeError('Aggregator type not implemented')
            if isinstance(agg_val, float):
                agg_val = round(agg_val, 5)
        return agg_val

class AggregatorParser:
    """This class contains functionality for parsing :class:`~graphxplore.DataMapping.Conditionals.AggregatorOperator`
    and :class:`~graphxplore.DataMapping.Conclusions.AggregateConclusion` objects from and to string.
    """
    @staticmethod
    def from_string(input_str : str) -> Optional[Tuple[str, str, DataType, AggregatorType]]:
        """Parses a table, variable, data type and aggregator type from a string. If the string is invalid ``None`` is
        returned.

        :param input_str: The string to parse
        :return: Returns a tuple with the parsed data, or ``None`` if the string could not be parsed
        """
        if not input_str.startswith('AGGREGATE '):
            return None
        # split into 10 parts
        literals = input_str.split(maxsplit=9)
        if len(literals) != 10:
            return None
        # cut comparisons if present
        if '' in literals[9]:
            literals[9] = literals[9].split()[0]
        aggregator = literals[1]
        if aggregator not in AggregatorType._value2member_map_:
            return None
        aggregator = AggregatorType(aggregator)
        if literals[2] != 'VARIABLE':
            return None
        var = literals[3]
        if literals[5] != 'TYPE':
            return None
        data_type = literals[6]
        if data_type not in DataType._value2member_map_:
            return None
        data_type = DataType[data_type]
        if literals[8] != 'TABLE':
            return None
        table = literals[9]
        return table, var, data_type, aggregator

    @staticmethod
    def to_str(table : str, var : str, data_type : DataType, aggregator : AggregatorType) -> str:
        """Converts data of :class:`~graphxplore.DataMapping.Conditionals.AggregatorOperator` and
        :class:`~graphxplore.DataMapping.Conclusions.AggregateConclusion` objects to string.

        :param table: The table of variable to aggregate
        :param var: The name of the variable to aggregate
        :param data_type: The data type of values that should be aggregated
        :param aggregator: The type of aggregation
        :return: Returns the parsed string
        """
        return 'AGGREGATE ' + aggregator + ' VARIABLE ' + var + ' OF TYPE ' + data_type + ' IN TABLE ' + table

    @staticmethod
    def check_compatibility(table : str, var : str, data_type : DataType, aggregator : AggregatorType,
                            list_aggregation_allowed : bool = True) -> None:
        """Checks if data type and aggregation type match. String values can only be counted or concatenated. For
        :class:`~graphxplore.DataMapping.Conditionals.AggregatorOperator` the ``AggregatorType.List`` type is also valid
        for all data types.

        :param table: The table of variable to aggregate
        :param var: The name of the variable to aggregate
        :param data_type: The data type of values that should be aggregated
        :param aggregator: The type of aggregation
        :param list_aggregation_allowed: If ``True`` the ``AggregatorType.List`` type is also valid
        :return:
        """
        if data_type == DataType.String:
            valid_string_aggregators = [AggregatorType.Concatenate, AggregatorType.Count]
            if list_aggregation_allowed:
                valid_string_aggregators.append(AggregatorType.List)
            if aggregator not in valid_string_aggregators:
                raise AttributeError('The aggregator type "' + aggregator
                                     + '" is invalid for string value aggregation of variable "' + var
                                     + '" of table "' + table + '". Possible aggregator types are: "'
                                     + '", "'.join(valid_string_aggregators) + '"')

    @staticmethod
    def get_aggregated_data_type(aggregator : AggregatorType) -> Optional[DataType]:
        """Returns the data type of the aggregation (not the type of cell values that should be aggregated).

        :param aggregator: The type of aggregation
        :return: Returns the data, or ``None`` if the type is ``AggregatorType.List`` (is a list, has to basic data type)
        """
        # list is not a basic data type
        if aggregator == AggregatorType.List:
            return None
        if aggregator == AggregatorType.Count:
            return DataType.Integer
        if aggregator == AggregatorType.Concatenate:
            return DataType.String
        if aggregator in [AggregatorType.Min, AggregatorType.Max, AggregatorType.Mean, AggregatorType.Sum,
                          AggregatorType.Std, AggregatorType.Median, AggregatorType.Amplitude]:
            return DataType.Decimal
        raise NotImplemented('Aggregator type not implemented')

class AggregatedData:
    """This class stores all aggregated data (of other variables) for a fixed primary key value.
    """
    def __init__(self):
        """Constructor method
        """
        # table -> aggregated variable -> (aggregated data type, aggregation type) -> aggregated value
        self.aggregated_data = collections.defaultdict(lambda : collections.defaultdict(dict))

    def get_variable_aggregation(self, table : str, variable : str, data_type : DataType,
                                 agg_type : AggregatorType) -> Optional[Union[str, int, float, Set[str]]]:
        """Returns data aggregation value for a specific variable, data type and aggregation type.

        :param table: The table of the aggregated variable
        :param variable: The name of the aggregated variable
        :param data_type: The data type of values that were aggregated
        :param agg_type: The type of aggregation
        :return: Returns the aggregated value or ``None`` if no data was aggregated
        """
        if table not in self.aggregated_data:
            raise AttributeError('Table "' + table + '" not found in aggregated source data')
        if variable not in self.aggregated_data[table]:
            raise AttributeError('Variable "' + variable + '" for table "' + table
                                 + '" not found in aggregated source data')
        pair = (data_type, agg_type)
        if pair not in self.aggregated_data[table][variable]:
            raise AttributeError('Aggregated data of type "' + agg_type + '" for values of data type "'
                                 + data_type + '" of variable "' + variable + '" in table "' + table
                                 + '" does not exist in aggregated source data')
        return self.aggregated_data[table][variable][pair]

    def add_variable_aggregation(self, table : str, variable : str, data_type : DataType,
                                 agg_type : AggregatorType, value : Optional[Union[str, int, float, Set[str]]]) -> None:
        """Adds a data aggregation value for a specific variable, data type and aggregation type for this specific
        primary key value.

        :param table: The table of the aggregated variable
        :param variable: The name of the aggregated variable
        :param data_type: The data type of values that were aggregated
        :param agg_type: The type of aggregation
        :param value: The aggregated value or ``None`` if no data was aggregated
        """
        pair = (data_type, agg_type)
        if (table in self.aggregated_data
                and variable in self.aggregated_data[table]
                and pair in self.aggregated_data[table][variable]):
            raise AttributeError('Aggregated data already exists for table "' + table + '", variable "' + variable
                                 + '", data type ' + data_type + ' and aggregator type ' + agg_type)
        self.aggregated_data[table][variable][pair] = value

    def exists(self, table : str, variable : str, data_type : DataType, agg_type : AggregatorType) -> bool:
        """Checks if some value or ``None`` exists for this table, variable, data type and aggregation type in the
        data structure.

        :param table: The table of the aggregated variable
        :param variable: The name of the aggregated variable
        :param data_type: The data type of values that were aggregated
        :param agg_type: The type of aggregation
        :return: Returns ``True`` if some value or ``None`` exists in the data structure for the specified parameters
        """
        return (table in self.aggregated_data
                and variable in self.aggregated_data[table]
                and (data_type, agg_type) in self.aggregated_data[table][variable])

    def merge(self, other : 'AggregatedData') -> 'AggregatedData':
        """Merges two data structures. Raises an exception if different aggregation values were assigned to the same
        configuration of table, variable, data type and aggregation type.

        :param other: The other data structure that should be merged with this one
        :return: Returns a new merged data structure
        """
        result = AggregatedData()
        result.aggregated_data = copy.deepcopy(self.aggregated_data)
        for table, table_data in other.aggregated_data.items():
            if table not in result.aggregated_data:
                result.aggregated_data[table] = copy.deepcopy(table_data)
                continue
            for var, aggregations in table_data.items():
                if var not in result.aggregated_data[table]:
                    result.aggregated_data[table][var] = copy.deepcopy(aggregations)
                    continue
                for (data_type, agg_type), agg_val in aggregations.items():
                    if (data_type, agg_type) not in result.aggregated_data[table][var]:
                        result.aggregated_data[table][var][(data_type, agg_type)] = copy.deepcopy(agg_val)
                    else:
                        this_val = result.aggregated_data[table][var][(data_type, agg_type)]
                        if this_val is None:
                            result.aggregated_data[table][var][(data_type, agg_type)] = copy.deepcopy(agg_val)
                        elif agg_val is not None and this_val != agg_val:
                                raise AttributeError('Cannot merge aggregated data objects, because aggregated data '
                                                     'for variable "' + var + '" of table "' + table + '", data type '
                                                     + data_type + ' and aggregation type ' + agg_type
                                                     + ' is contained in both objects and values differ')
        return result