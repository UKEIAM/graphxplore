import collections
import copy
from dataclasses import asdict
from typing import Optional, Dict, Union, List
from graphxplore.Basis import RelationalDataIODevice
from graphxplore.MetaDataHandling import MetaData, VariableInfo, DataType, VariableType
from .data_mapping import DataMapping, TableMapping
from .variable_mapping import VariableMapping, MappingCase
from .data_transformation import DataTransformation
from .Conclusions import CopyConclusion
from .Conditionals import AlwaysTrueOperator, InListOperator, NegatedOperator
from .data_structure_transformer import SourceDataType, TableMappingType

class DataMappingUtils:
    """This class contains static utility methods for data cleaning or adding primary keys.
    """
    @staticmethod
    def copy_variable(source_meta : MetaData, source_table : str, source_var : str, target_meta : MetaData,
                      target_table : str, target_var : str, delete_artifacts : bool = False) -> VariableMapping:
        """Generates a variable mapping for copying a source variable to a target variable,
        optionally deleting artifacts. The target variable is added to ``target_meta`` if it
        doesn't exist yet.

        :param source_meta: The source metadata
        :param source_table: The source table
        :param source_var: The name of the source variable
        :param target_meta: The target metadata, ``target_table`` must already exist as a table
        :param target_table: The target table
        :param target_var: The name of the target variable
        :param delete_artifacts: If ``True`` artifacts are removed while copying
        :return: Returns the variable mapping
        """
        if target_table not in target_meta.get_table_names():
            raise AttributeError('Table "' + target_table + '" not in target meta data')
        if target_var not in target_meta.get_variable_names(target_table):
            source_var_info = source_meta.get_variable(source_table, source_var)
            var_dict = asdict(source_var_info)
            var_dict['table'] = target_table
            target_meta.data[target_table]['variables'][target_var] = VariableInfo.from_dict(target_var, target_table,
                                                                                             var_dict)
            target_var_info = target_meta.get_variable(target_table, target_var)
            if target_var_info.variable_type == VariableType.PrimaryKey:
                target_meta.assign_primary_key(target_table, target_var)
        else:
            target_var_info = target_meta.get_variable(target_table, target_var)
        if not delete_artifacts and target_var_info.artifacts is not None:
            data_type = DataType.String
        else:
            data_type = target_var_info.data_type
        conclusion = CopyConclusion(data_type, source_table, source_var)
        to_delete = []
        if delete_artifacts and target_var_info.artifacts is not None:
            to_delete += target_var_info.artifacts
            target_var_info.artifacts = None
        if len(to_delete) == 0:
            conditional = AlwaysTrueOperator()
        else:
            conditional = NegatedOperator(InListOperator(source_table, source_var, data_type,
                                                         to_delete))
        return VariableMapping(target_table, target_var, [MappingCase(conditional, conclusion)])

    @staticmethod
    def get_copy_mapping(source_meta : MetaData, target_meta : MetaData, delete_artifacts : bool = False) -> DataMapping:
        """Generates mappings for copying all data from a source dataset, optionally deleting artifacts.
        ``target_meta`` is filled with all variables from the source dataset, but tables have to exist already.
        Foreign key relations are inferred from ``source_meta`` if they do not exist already.

        :param source_meta: The source metadata
        :param target_meta: The target metadata, tables must exist and be identical with the source metadata
        :param delete_artifacts: If ``True``, artifacts are removed while copying
        :return: Returns the data mapping
        """
        var_mappings = collections.defaultdict(dict)
        for source_table in source_meta.get_table_names():
            if not source_meta.has_primary_key(source_table):
                raise AttributeError('Before copying, the source table "' + source_table
                                     + '" needs an assigned primary key')
            pk = source_meta.get_primary_key(source_table)
            if not target_meta.has_primary_key(source_table):
                if pk not in target_meta.get_variable_names(source_table):
                    source_var_info = source_meta.get_variable(source_table, pk)
                    var_dict = asdict(source_var_info)
                    target_meta.data[source_table]['variables'][pk] = VariableInfo.from_dict(
                        pk, source_table, var_dict)
                target_meta.assign_primary_key(source_table, pk)
            for source_var in source_meta.get_variable_names(source_table):
                if source_var == pk:
                    continue
                var_mapping = DataMappingUtils.copy_variable(source_meta, source_table, source_var, target_meta,
                                                             source_table, source_var, delete_artifacts)
                var_mappings[source_table][source_var] = var_mapping
        table_mappings = {table : TableMapping(TableMappingType.OneToOne, [table])
                          for table in source_meta.get_table_names()}
        for table in target_meta.get_table_names():
            target_fks = target_meta.get_foreign_keys(table)
            if len(target_fks) == 0:
                target_meta.data[table]["foreign_keys"] =  source_meta.get_foreign_keys(table)
        return DataMapping(source_meta, target_meta, table_mappings, var_mappings)

    @staticmethod
    def copy_dataset(source_meta : MetaData, data_source : Union[str, Dict[str, List[Dict[str, str]]]],
                     data_target : Union[str, Dict[str, List[Dict[str, str]]]], delete_artifacts : bool = False,
                     source_file_encoding : Optional[str] = None) -> None:
        """Copies a whole dataset while optionally deleting artifacts.

        :param source_meta: The source metadata
        :param data_source: The path to a directory where the CSV files are read from or a data dictionary where data is
            retrieved
        :param data_target: The path to a directory where the resulting CSV files are written to or a data dictionary
            where data is inserted
        :param delete_artifacts: If ``True`` artifacts are removed while copying
        :param source_file_encoding: Specifies the file encoding of all source tables, if read from a CSV. Will be
            detected if not specified, defaults to ``None``
        """
        target_meta = MetaData(source_meta.get_table_names())
        mappings = DataMappingUtils.get_copy_mapping(source_meta, target_meta, delete_artifacts)
        data_transformation = DataTransformation(mappings)
        data_transformation.transform_to_target(SourceDataType.CSV, data_source, data_target,
                                                source_file_encoding=source_file_encoding)

    @staticmethod
    def add_primary_key(data_source : Union[str, Dict[str, List[Dict[str, str]]]], source_table : str,
                        data_target : Union[str, Dict[str, List[Dict[str, str]]]], target_table : str,
                        primary_key : str, start_idx : int = 0,
                        file_encoding : Optional[str] = None) -> int:
        """Adds an integer primary key to each row of the source table and stores the result in a data target.

        :param data_source: The path to a directory where the CSV file is read from or a data dictionary where data is
            retrieved
        :param source_table: The name of the source table
        :param data_target: The path to a directory where the resulting CSV file is written to or a data dictionary
            where data is inserted
        :param target_table: The name of the resulting target table
        :param primary_key: The name of the primary key
        :param start_idx: The start index for the primary key, defaults to 0
        :param file_encoding: The file encoding of the CSV file (ascii, utf-8,...) in chardet definition.
            Is guessed if not specified, defaults to None
        :return: Returns the largest assigned primary key value
        """
        available_tables = RelationalDataIODevice.get_available_table_names(data_source)
        if source_table not in available_tables:
            raise AttributeError('Source table "' + source_table + '" does not exist in data source')
        RelationalDataIODevice.check_data_location(data_target, write=True)
        with RelationalDataIODevice(data_source, source_table, file_encoding=file_encoding) as reader:
            header = reader.get_header()
            if primary_key in header:
                raise AttributeError('Specified attribute name "' + primary_key
                                     + '" for primary key is already contained in source table')
            header_with_pk = [primary_key] + list(header)
            with RelationalDataIODevice(data_target, target_table, write=True, header=header_with_pk) as writer:
                idx = start_idx
                for input_line in reader:
                    output_line = copy.deepcopy(input_line)
                    output_line[primary_key] = idx
                    writer.writerow(output_line)
                    idx += 1
                return idx

    @staticmethod
    def pivot_table(source_table: List[Dict[str, str]], index_column: str, value_column: str,
                    to_index: Optional[Dict[str, str]] = None,
                    columns_to_keep: Optional[List[str]] = None) -> List[Dict[str, str]]:

        header = source_table[0].keys()
        if index_column not in header:
            raise AttributeError('Index column "' + index_column + '" not found in source table')
        if value_column not in header:
            raise AttributeError('Value column "' + value_column + '" not found in source table')
        if index_column == value_column:
            raise AttributeError('Index column and value column cannot both be "' + index_column + '"')
        if columns_to_keep is not None:
            if index_column in columns_to_keep:
                raise AttributeError('Index column "' + index_column
                                     + '" in "columns_to_keep", but it will be used for pivotization')
            if value_column in columns_to_keep:
                raise AttributeError('Value column "' + value_column
                                     + '" in "columns_to_keep", but it will be used to fill pivot columns in result'
                                       ' table')
            for column in columns_to_keep:
                if column not in header:
                    raise AttributeError('Column "' + column + '" marked for keeping, but not found in source table')
            target_header = copy.deepcopy(columns_to_keep)
        else:
            target_header = [column for column in header if column not in [index_column, value_column]]
        index_vals = set(row[index_column] for row in source_table)
        if to_index is not None:
            for index_val, target_column in to_index.items():
                if index_val not in index_vals:
                    raise AttributeError('Value to index "' + index_val + '" not found in index column "'
                                         + index_column + '"')
                if target_column in target_header:
                    raise AttributeError('Index target column name "' + target_column
                                         + '" already existing as column name')
            target_header += list(to_index.values())
        else:
            target_header += list(index_vals)
        result = []
        for source_row in source_table:
            index_row_val = source_row[index_column]
            if to_index is not None:
                if index_row_val not in to_index:
                    continue
            target_row = {column: '' if column not in source_row else source_row[column] for column in target_header}
            if to_index is not None:
                target_row[to_index[index_row_val]] = source_row[value_column]
            else:
                target_row[index_row_val] = source_row[value_column]
            result.append(target_row)
        return result










