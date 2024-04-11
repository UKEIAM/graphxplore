import collections
import copy
from typing import Union, Mapping, Iterable, Dict, Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass
from .meta_lattice import MetaLattice
from .data_aggregator import AggregatedData, AggregatorType, CSVDataAggregator
from graphxplore.MetaDataHandling import MetaData, DataType
from graphxplore.Basis import RelationalDataIODevice

class TableMappingType(str, Enum):
    """The type of mapping for a target table: One-to-one relation to a single source table, or one-to-many
    relation to multiple source tables by merging (combination of rows with same primary key value) or concatenation
    (processing each table independently. Lastly, the mapping relation can be inherited from an ancestor source table
    (inverted foreign table chain).
    """
    OneToOne = 'OneToOne'
    Inherited = 'Inherited'
    Concatenate = 'Concatenate'
    Merge = 'Merge'

@dataclass
class SourceDataLine:
    """One flattened line of source data optionally containing aggregated data as well.

    :param singular_data: The flattened line of data
    :param aggregated_data: The data that was aggregated for the root primary key of this line, defaults to ``None``
    """
    singular_data : Dict[str, Dict[str, Optional[Union[str, int, float]]]]
    aggregated_data : Optional[AggregatedData] = None

    def get_singular_value(self, table : str, variable : str) -> Optional[Union[str, int, float]]:
        """Retrieves the value of ``variable`` contained in this source data line, if ``variable`` was not aggregated

        :param table: The table of ``variable``
        :param variable: The variable name
        :return:
        """
        if table not in self.singular_data:
            raise AttributeError('Table "' + table + '" not found in source data')
        if variable not in self.singular_data[table]:
            raise AttributeError('Variable "' + variable + '" for table "' + table + '" not found in source data')
        return self.singular_data[table][variable]

class SourceDataType(str, Enum):
    """The type of source data: A directory with CSV files, or a Neo4J database.
    """
    CSV = 'CSV'
    Database = 'Database'

@dataclass
class FlattenerLatticeConfig:
    """This class contains the lattice and required variables that are needed for flattening data starting from a set
    of source tables. Optionally, lattice and variables for data aggregation are given as well if required.

    :param singular_lattice: A minimal sub-lattice of the source data containing all tables of `required_singular_vars`
    :param required_singular_vars: All variables needed for data flattening with singular values
    :param aggregation_lattice: A minimal sub-lattice of ancestor tables containing all tables of
    `required_aggregation_vars`, defaults to None
    :param required_aggregation_vars: All variables needed for data flattening with aggregated values, defaults to None
    """
    singular_lattice : MetaLattice
    required_singular_vars : Mapping[str, Iterable[str]]
    aggregation_lattice : Optional[MetaLattice] = None
    required_aggregation_vars : Optional[Mapping[str, Mapping[str, Iterable[Tuple[AggregatorType, DataType]]]]] = None

class MinimalTableDataReader:
    """This is the parent class of all classes reading data from one or multiple minimal source tables in the
    definition of :class:`MetaLattice`, e.g. they are never referenced as foreign tables. The class and its children
    function as iterable context managers.

    :param meta: The :class:`MetaData` of the source dataset
    :param data_source: The path to a directory with CSV files or a data dictionary containing the source dataset
    :param minimal_tables: All currently considered minimal tables
    :param required_vars: All variables required for the currently considered part of the mapping process
    :param file_encoding: Specifies the file encoding for all minimal tables. Will be detected if not specified, defaults to None
    """
    def __init__(self, meta : MetaData, data_source: Union[str, Dict[str, List[Dict[str, str]]]], minimal_tables : Iterable[str],
                 required_vars : Mapping[str, Iterable[str]], file_encoding : Optional[str] = None):
        self.meta = meta
        self.data_source = data_source
        available_tables = RelationalDataIODevice.get_available_table_names(data_source)
        for table in minimal_tables:
            if table not in available_tables:
                raise AttributeError('Minimal table "' + table + '" does not exist in data source')
        self.tables = list(minimal_tables)
        self.required_vars = required_vars
        self.encoding = file_encoding

    def __enter__(self):
        raise NotImplemented('Never call abstract class')

    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplemented('Never call abstract class')

    def __iter__(self):
        return self

    def __next__(self) -> Dict[str, Dict[str, Union[str, int, float]]]:
        raise NotImplemented('Never call abstract class')

class CopyTableReader(MinimalTableDataReader):
    """This class reads data from a single minimal source table that has a one-to-one mapping with a target table.

    :param meta: The :class:`MetaData` of the source dataset
    :param data_source: The path to a directory with CSV files or a data dictionary containing the source dataset
    :param minimal_table: All currently considered minimal tables
    :param required_vars: All variables required for the currently considered part of the mapping process
    :param file_encoding: Specifies the file encoding of the minimal table. Will be detected if not specified, defaults to None
    """
    def __init__(self, meta : MetaData, data_source: Union[str, Dict[str, List[Dict[str, str]]]], minimal_table: str,
                 required_vars: Mapping[str, Iterable[str]], file_encoding : Optional[str] = None):
        super().__init__(meta, data_source, [minimal_table], required_vars, file_encoding)
        self.reader = None

    def __enter__(self):
        print('Start reading dynamic table ' + self.tables[0])
        self.reader = RelationalDataIODevice(self.data_source, self.tables[0], file_encoding=self.encoding).__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reader.__exit__(exc_type, exc_val, exc_tb)

    def __next__(self) -> Dict[str, Dict[str, Union[str, int, float]]]:
        line = next(self.reader)
        return {self.tables[0] : line}

class MergeTableReader(MinimalTableDataReader):
    """This class reads data from multiple minimal source tables and merges data where the same primary key values
    appear in different tables.

    :param meta: The :class:`MetaData` of the source dataset
    :param data_source: The path to a directory with CSV files or a data dictionary containing the source dataset
    :param minimal_tables: All currently considered minimal tables
    :param required_vars: All variables required for the currently considered part of the mapping process
    :param file_encoding: Specifies the file encoding for all minimal tables. Will be detected if not specified, defaults to None
    """
    def __init__(self, meta : MetaData, data_source: Union[str, Dict[str, List[Dict[str, str]]]], minimal_tables: Iterable[str],
                 required_vars: Mapping[str, Iterable[str]], file_encoding : Optional[str] = None):
        super().__init__(meta, data_source, minimal_tables, required_vars, file_encoding)
        self.data = []
        self.iter = None

    def __enter__(self):
        merge_data = collections.defaultdict(dict)
        for table in self.tables:
            primary_key = self.meta.get_primary_key(table)
            foreign_keys = self.meta.get_foreign_keys(table).keys()
            with RelationalDataIODevice(self.data_source, table, file_encoding=self.encoding) as reader:
                print('Loading data from table to merge: ' + table)
                for line in reader:
                    merge_data[line[primary_key]][table] = {var: val for var, val in line.items()
                                                            if var == primary_key
                                                            or var in foreign_keys
                                                            or (table in self.required_vars
                                                                and var in self.required_vars[table])}
        self.data = [line_dicts for primary_key, line_dicts in sorted(merge_data.items())]
        self.iter = iter(self.data)
        del merge_data
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.data

    def __next__(self) -> Dict[str, Dict[str, Union[str, int, float]]]:
        return next(self.iter)

class ConcatenateTableReader(MinimalTableDataReader):
    """This class reads data from multiple minimal source tables one after another, not merging data for the same
    primary keys.

    :param meta: The :class:`MetaData` of the source dataset
    :param data_source: The path to a directory with CSV files or a dictionary containing the source dataset
    :param minimal_tables: All currently considered minimal tables
    :param required_vars: All variables required for the currently considered part of the mapping process
    :param file_encoding: Specifies the file encoding for all minimal tables, defaults to None
    """
    def __init__(self, meta : MetaData, data_source: Union[str, Dict[str, List[Dict[str, str]]]], minimal_tables: Iterable[str],
                 required_vars: Mapping[str, Iterable[str]], file_encoding : Optional[str] = None):
        super().__init__(meta, data_source, minimal_tables, required_vars, file_encoding)
        self.reader = None
        self.table_iter = iter(self.tables)
        self.current_table = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reader.__exit__(exc_type, exc_val, exc_tb)

    def __next__(self) -> Dict[str, Dict[str, Union[str, int, float]]]:
        try:
            line = next(self.reader)
        # TypeError thrown when self.reader is still None
        except (StopIteration, TypeError):
            # throws correct StopIteration (not excepted) when all tables are read
            self.current_table = next(self.table_iter)
            self.reader = RelationalDataIODevice(self.data_source, self.current_table, file_encoding=self.encoding).__enter__()
            print('Start reading dynamic table ' + self.current_table)
            line = next(self.reader)
        primary_key = self.meta.get_primary_key(self.current_table)
        foreign_keys = self.meta.get_foreign_keys(self.current_table).keys()
        trimmed_line = {var: val for var, val in line.items()
                        if var == primary_key
                        or var in foreign_keys
                        or (self.current_table in self.required_vars
                            and var in self.required_vars[self.current_table])}
        return {self.current_table : trimmed_line}

class DataFlattener:
    """This class is the parent of all classes reading data from a source dataset and resolving all foreign key
    relations based on one or multiple minimal tables. As a result, the source data is "flattened" to single rows of
    data instead of spread across multiple tables. The class and all its children functions as an iterable context
    manager.

    :param source_type: The type of the source data
    :param meta: The metadata of the source data
    :param mapping_type: the mapping type of the currently considered minimal target table
    :param lattice_config: The lattices and required variables for singular and optionally aggregated source data retrieval
    """
    def __init__(self, source_type : SourceDataType, meta: MetaData, mapping_type : TableMappingType,
                 lattice_config : FlattenerLatticeConfig):
        if lattice_config.aggregation_lattice is None != lattice_config.required_aggregation_vars is None:
            raise AttributeError('For data aggregation either both lattice and required variables must be specified, '
                                 'or none')
        self.meta = meta
        self.lattice_config = lattice_config
        self.source_type = source_type
        self.mapping_type = mapping_type
        self.should_aggregate = lattice_config.aggregation_lattice is not None
        self.aggregator = None

    def __enter__(self):
        raise NotImplemented('Never call abstract class')

    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplemented('Never call abstract class')

    def __iter__(self):
        return self

    def __next__(self) -> SourceDataLine:
        raise NotImplemented('Never call abstract class')

class CSVDataFlattener(DataFlattener):
    """This class reads data from CSV files and "flattens" all primary/foreign key relations to single rows given
    a :class:`MetaLattice` representing a subset of the source dataset.

    :param meta: The metadata of the source data
    :param data_source: The path to a directory with CSV files or a dictionary containing the source dataset
    :param mapping_type: the mapping type of the currently considered minimal target table
    :param lattice_config: The lattices and required variables for singular and optionally aggregated source data retrieval
    :param file_encoding: Specifies the file encoding of all read CSV tables. Will be detected if not specified,
        defaults to None
    """
    def __init__(self, meta: MetaData, data_source: Union[str, Dict[str, List[Dict[str, str]]]], mapping_type : TableMappingType,
                 lattice_config : FlattenerLatticeConfig, file_encoding : Optional[str] = None):
        super().__init__(SourceDataType.CSV, meta, mapping_type, lattice_config)
        RelationalDataIODevice.check_data_location(data_source)
        self.data_source = data_source
        self.data = {}
        self.minimal_reader = None
        self.file_encoding = file_encoding

    def __enter__(self):
        if self.mapping_type == TableMappingType.OneToOne:
            if len(self.lattice_config.singular_lattice.min_elements) != 1:
                raise AttributeError('When copying a primary key, only a single source primary key must be specified')
            minimal_table = next(iter(self.lattice_config.singular_lattice.min_elements))
            self.minimal_reader = CopyTableReader(self.meta, self.data_source,
                                                  minimal_table, self.lattice_config.required_singular_vars,
                                                  self.file_encoding).__enter__()
        elif self.mapping_type == TableMappingType.Concatenate:
            self.minimal_reader = ConcatenateTableReader(self.meta, self.data_source,
                                                         self.lattice_config.singular_lattice.min_elements,
                                                         self.lattice_config.required_singular_vars,
                                                         self.file_encoding).__enter__()
        elif self.mapping_type == TableMappingType.Merge:
            self.minimal_reader = MergeTableReader(self.meta, self.data_source,
                                                   self.lattice_config.singular_lattice.min_elements,
                                                   self.lattice_config.required_singular_vars,
                                                   self.file_encoding).__enter__()
        else:
            raise NotImplemented('Mapping type of primary key not implemented')

        if self.should_aggregate:
            self.aggregator = CSVDataAggregator(self.data_source, self.meta, self.lattice_config.aggregation_lattice,
                                                self.lattice_config.required_aggregation_vars, self.file_encoding)
            self.aggregator.aggregate_data()

        for table, parents in self.lattice_config.singular_lattice.parents.items():
            # minimal table read on the fly (not statically)
            if len(parents) == 0:
                continue
            primary_key = self.meta.get_primary_key(table)
            foreign_keys = self.meta.get_foreign_keys(table).keys()
            with RelationalDataIODevice(self.data_source, table, file_encoding=self.file_encoding) as reader:
                table_data = {line[primary_key] : {var : val for var, val in line.items() if var == primary_key
                                                   or var in foreign_keys
                                                   or (table in self.lattice_config.required_singular_vars
                                                       and var in self.lattice_config.required_singular_vars[table])}
                              for line in reader}
                self.data[table] = table_data
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.minimal_reader.__exit__(exc_type, exc_val, exc_tb)

    def __next__(self) -> SourceDataLine:
        result = {}
        dynamic_lines = next(self.minimal_reader)

        for table, table_line in dynamic_lines.items():
            self.__add_values_rec(table, table_line, result)

        for table, table_vars in self.lattice_config.required_singular_vars.items():
            if table not in result:
                result[table] = {var : None for var in table_vars}
        if self.should_aggregate:
            aggregated_data = AggregatedData()
            for start_table in self.lattice_config.aggregation_lattice.max_elements:
                start_pk_val = result[start_table][self.meta.get_primary_key(start_table)]
                if start_pk_val is not None:
                    aggregated_data = aggregated_data.merge(self.aggregator.aggregated_data[start_table][start_pk_val])
        else:
            aggregated_data = None

        return SourceDataLine(singular_data=result, aggregated_data=aggregated_data)

    def __add_values_rec(self, current_table : str, current_line : dict, result : dict) -> None:
        """Recursively traverses the :class:`MetaLattice` and adds the required data to the "flattened" output.

        :param current_table: The current table in the recursion
        :param current_line: The data row of ``current_table``
        :param result: The flattened result line
        """
        primary_key = self.meta.get_primary_key(current_table)
        pk_value = current_line[primary_key]
        table_result = {primary_key : pk_value}
        if current_table in self.lattice_config.required_singular_vars:
            for variable in self.lattice_config.required_singular_vars[current_table]:
                table_result[variable] = current_line[variable]
        result[current_table] = table_result
        for child in self.lattice_config.singular_lattice.children[current_table]:
            if child in result:
                continue
            foreign_key = self.meta.get_primary_key(child)
            foreign_key_value = current_line[foreign_key]
            child_line = self.data[child][foreign_key_value]
            self.__add_values_rec(child, child_line, result)


class DataSegmentor:
    """This abstract class and all its children are the counterpart of the :class:`DataFlattener`. They take a line of
    data and distribute it among the various foreign tables.

    :param meta: The metadata of the target dataset
    :param lattice: The lattice of the whole target dataset
    :param inheriting_tables: The tables (keys of dictionary) for which the primary key should be automatically
        generated via a uniqueness check, because they inherit the relation from other target tables (value of dictionary)
    :param data_target: The path to a directory where CSV files are written or a data dictionary where data is inserted
    :param global_unique_keys: If ``True`` the automatically generated primary key values will be unique across the
        dataset, defaults to ``False``
    """
    def __init__(self, meta : MetaData, lattice : MetaLattice, inheriting_tables : Dict[str, str],
                 data_target : Union[str, Dict[str, List[Dict[str, str]]]], global_unique_keys : bool = False):
        self.inheriting_tables = inheriting_tables
        self.lattice = lattice
        self.meta = meta
        self.global_unique = global_unique_keys
        RelationalDataIODevice.check_data_location(data_target, write=True)
        self.data_target = data_target
        self.auto_data = {table : {'max_id' : 0, 'rows' : {}} for table in self.inheriting_tables.keys()}
        self.files = []
        self.writers = {}

    def __enter__(self):
        for table in self.meta.get_table_names():
            if table not in self.auto_data:
                writer = RelationalDataIODevice(self.data_target, table, write=True,
                                                header=self.meta.get_variable_names(table)).__enter__()
                self.writers[table] = writer
        return self

    def write_row(self, sub_lattice : MetaLattice, row: Dict[str, Dict[str, Optional[Union[str, int, float]]]]) -> None:
        """Takes a single line of data and distributes it among the target dataset

        :param sub_lattice: The sub-lattice starting at the currently considered target table and
            containing all inheriting related tables
        :param row: The line of data to be distributed
        """
        auto_key_values = {table: None for table in self.auto_data}
        visited = set()
        queue = copy.deepcopy(sub_lattice.max_elements)
        while len(queue) > 0:
            current_table = queue.pop(0)
            self.__segment_data(current_table, row, auto_key_values)
            visited.add(current_table)
            for parent in sub_lattice.parents[current_table]:
                if parent not in visited:
                    queue.append(parent)

    def __segment_data(self, current_table: str, row: Dict[str, Dict[str, Optional[Union[str, int, float]]]],
                       auto_key_values: Dict[str, int]) -> None:
        """Selects the share of the data line which is written to ``current_table`` and keeps track of the generated
        automatically generated keys. If ``current_table`` is "automatic", the generated keys are added to
        ``auto_key_values``.

        :param current_table: The name of the currently considers table for data distribution
        :param row: The full line of data
        :param auto_key_values: The values of the automatically generated keys
        """
        if current_table not in row:
            raise AttributeError('Table ' + current_table + ' missing in row data')
        primary_key = self.meta.get_primary_key(current_table)
        line_dict = dict([(var, val) if val is not None else (var, '') for var, val in row[current_table].items()])
        # fill up with auto generated keys
        for foreign_key, foreign_table in self.meta.get_foreign_keys(current_table).items():
            if foreign_table in self.auto_data:
                line_dict[foreign_key] = auto_key_values[foreign_table]
        for variable in self.meta.get_variable_names(current_table):
            if variable not in line_dict and (variable != primary_key or current_table not in self.auto_data):
                raise AttributeError('Variable "' + variable + '" of table "' + current_table + '" missing in row data')
        # write to cache
        if current_table in self.auto_data:
            sorted_line = tuple(line_dict[var] for var in self.meta.get_variable_names(current_table)
                                if var != primary_key)
            if sorted_line not in self.auto_data[current_table]['rows']:
                idx = self.auto_data[current_table]['max_id']
                line_dict[primary_key] = idx
                self.auto_data[current_table]['rows'][sorted_line] = line_dict
                if self.global_unique:
                    for table, table_dict in self.auto_data:
                        table_dict['max_id'] += 1
                else:
                    self.auto_data[current_table]['max_id'] += 1
            else:
                cached_line = self.auto_data[current_table]['rows'][sorted_line]
                idx = cached_line[primary_key]
            auto_key_values[current_table] = idx
        # directly write to file
        else:
            self.writers[current_table].writerow(line_dict)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for writer in self.writers.values():
            writer.__exit__(exc_type, exc_val, exc_tb)
        # finished without exception, write cache to files
        if exc_type is None:
            for table, table_data in self.auto_data.items():
                with RelationalDataIODevice(self.data_target, table, write=True, header=self.meta.get_variable_names(table)) as writer:
                    for row in table_data['rows'].values():
                        writer.writerow(row)