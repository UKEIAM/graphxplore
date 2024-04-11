import os
import re
import json
import copy
from typing import List, Iterable, Dict, Optional
from .variable_info import VariableInfo, VariableType, DataType
from graphxplore.Basis import BaseUtils

class MetaData:
    """This class is the core of all ETL processes in graphxplore. It stores the metadata of a relational dataset.
    It contains information about its CSV tables, variables, primary/foreign keys,
    and much more information on the variable-level. For more information checkout :class:`VariableInfo`

    :param tables: The names of the CSV tables of the relational data set (without .csv)
    """
    def __init__(self, tables : Iterable[str]):
        """Constructor method
        """
        self.data = dict([(table, {'label' : table, 'primary_key' : '', 'foreign_keys' : {}, 'variables' : {}})
                          for table in tables])

    @staticmethod
    def load_from_json(filepath: str, file_encoding : Optional[str] = None) -> 'MetaData':
        """Reads a :class:`Metadata` object from a JSON.

        :param filepath: Path to the JSON
        :param file_encoding: file encoding of the JSON
        :return: Returns a Metadata object
        """
        if not os.path.isfile(filepath):
            raise AttributeError('Path "' + filepath +'" is not a valid file path')
        encoding = file_encoding if file_encoding is not None else BaseUtils.detect_file_encoding(filepath)
        with open(filepath, encoding=encoding) as f:
            data = json.load(f)
            return MetaData.from_dict(data)

    @staticmethod
    def from_dict(data : dict) -> 'MetaData':
        """Parses a :class:`Metadata` object from a dictionary.

        :param data: The input dictionary
        :return: Returns the parsed object
        """
        tables = data.keys()
        meta_data = MetaData(tables)
        for table in tables:
            table_data = data[table]
            if 'label' not in table_data or not isinstance(table_data['label'], str):
                raise AttributeError('Data for table "' + table
                                     + '" does not contain a string entry "label"')
            label = table_data['label']
            if 'variables' not in table_data or not isinstance(table_data['variables'], dict) \
                    or len(table_data['variables']) == 0:
                raise AttributeError('Data for table "' + table
                                     + '" does not contain a dictionary entry "variables" or any variable data')
            variables = {}
            for var_name, var_dict in table_data['variables'].items():
                variables[var_name] = VariableInfo.from_dict(var_name, table, var_dict)

            if 'primary_key' not in table_data or not isinstance(table_data['primary_key'], str):
                raise AttributeError('Data for table "' + table + '" does not contain a string entry "primary_key"')
            if table_data['primary_key'] == '':
                print('Table "' + table + '" has no primary key assigned')
            primary_key = table_data['primary_key']
            if primary_key != '' and (primary_key not in variables
                                      or variables[primary_key].variable_type != VariableType.PrimaryKey):
                raise AttributeError('Primary key "' + primary_key + '" for table "' + table
                                     + '" is not specified as variable of type "PrimaryKey" in table data')
            if 'foreign_keys' not in table_data or not isinstance(table_data['foreign_keys'], dict):
                raise AttributeError('Data for table "' + table + '" does not contain a list entry "foreign_keys')
            for foreign_key, foreign_table in table_data['foreign_keys'].items():
                if not isinstance(foreign_key, str) or not isinstance(foreign_table, str):
                    raise AttributeError('Foreign keys and foreign tables must be string entries')
                if foreign_table not in tables:
                    raise AttributeError('Foreign table "' + foreign_table
                                         + '" which was declared in data for table "' + table + '", does not exist')
                if foreign_key != data[foreign_table]['primary_key']:
                    raise AttributeError('Foreign key "' + foreign_key
                                         + '" is not the primary key in foreign table "' + foreign_table + '"')

                if foreign_key not in table_data['variables'] \
                        or table_data['variables'][foreign_key]['variable_type'] != VariableType.ForeignKey:
                    raise AttributeError('Foreign key "' + foreign_key + '" for table "' + table
                                         + '" is not specified as variable of type "ForeignKey" in table data')

            meta_data.data[table] = {'label': label, 'primary_key': primary_key,
                                     'foreign_keys': table_data['foreign_keys'], 'variables': variables}

        return meta_data

    def to_dict(self) -> dict:
        """Converts the object to a dictionary.

        :return: Returns the generated dictionary
        """
        output = {}
        for table, table_data in self.data.items():
            table_output = {
                'label' : table_data['label'],
                'primary_key' : table_data['primary_key'],
                'foreign_keys' : copy.deepcopy(table_data['foreign_keys']),
                'variables' : {var_name : var_info.to_dict() for var_name, var_info in table_data['variables'].items()}
            }
            output[table] = table_output
        return output


    def store_in_json(self, file_path: str, file_encoding : Optional[str] = None) -> None:
        """Stores the object as a JSON file.

        :param file_path: Path to the JSON
        :param file_encoding: file encoding that should be used for writing the JSON
        """
        dir_path = os.path.dirname(os.path.realpath(file_path))
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            raise AttributeError('File path "' + file_path
                                 + '" is invalid, since the containing directory does not exist')
        output_dict = self.to_dict()
        with open(file_path, "w", encoding=file_encoding) as f:
            json.dump(output_dict, f, indent=6, ensure_ascii=False)

    def __deepcopy__(self, memo : Dict={}) -> 'MetaData':
        result = MetaData(self.get_table_names())
        for table, table_data in self.data.items():
            result.data[table]['label'] = table_data['label']
            result.data[table]['primary_key'] = table_data['primary_key']
            result.data[table]['foreign_keys'] = copy.deepcopy(table_data['foreign_keys'])
            result.data[table]['variables'] = {var_name : VariableInfo.from_dict(var_name, table, var_info.to_dict())
                                               for var_name, var_info in table_data['variables'].items()}
        return result


    def add_table(self, table : str) -> None:
        """Add a table to the metadata

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        """
        if table in self.data:
            raise AttributeError('Table "' + table + '" already exists in meta data')
        self.data[table] =  {'label': table, 'primary_key': '', 'foreign_keys': {}, 'variables': {}}

    def remove_table(self, table : str) -> None:
        """Remove a table from the metadata. All foreign keys pointing to this table are changed to categorical
        variables

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        del self.data[table]
        for other in self.get_table_names():
            fks_of_table = [fk for fk, ft in self.get_foreign_keys(other).items() if ft == table]
            for fk in fks_of_table:
                del self.data[other]["foreign_keys"][fk]
                self.data[other]['variables'][fk].variable_type = VariableType.Categorical


    def assign_label(self, table : str, label : str) -> None:
        """Assigns a label to a table, e.g. describing the contained data. Existing labels will be overwritten

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :param label: The label that should be assigned, should not contain whitespace or line breaks
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        if not re.match("^[A-Za-z0-9-_]+$", label):
            raise AttributeError('Label "' + label + '" should only contain letters, numbers, hyphens and underscores')
        self.data[table]['label'] = label

    def add_variable(self, table : str, variable : str) -> VariableInfo:
        """Adds a variable for a specified table to the metadata.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :param variable: The name of the variable, i.e. the column name
        :return: Returns the generated variable info that can be filled
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        if variable in self.data[table]['variables']:
            raise AttributeError('Variable "' + variable + '" already exists in table "' + table + '"')
        self.data[table]['variables'][variable] = VariableInfo(name=variable, table = table,
                                                               labels=[],  variable_type=VariableType.Categorical,
                                                               data_type=DataType.String,
                                                               data_type_distribution=None)

        return self.data[table]['variables'][variable]

    def assign_primary_key(self, table : str, primary_key : str) -> None:
        """Assigns a primary key for the specified table. Raises an exception if ``table`` already has a primary key,
        or ``primary_key`` is not a variable of ``table``

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :param primary_key: The name of the primary key, i.e. the column name
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        if primary_key not in self.data[table]['variables']:
            raise AttributeError('Primary key "' + primary_key + '" is not a variable of table "' + table
                                 + '" in meta data')

        if self.data[table]['primary_key'] != '':
            raise AttributeError('Primary key already set for table "' + table + '"')

        self.data[table]['variables'][primary_key].variable_type = VariableType.PrimaryKey
        self.data[table]['primary_key'] = primary_key

    def change_primary_key(self, table : str, primary_key : str) -> None:
        """Changes the primary key for the specified table. Raises an exception if ``primary_key`` is not a variable
        of ``table``

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :param primary_key: The name of the primary key, i.e. the column name
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        if primary_key not in self.data[table]['variables']:
            raise AttributeError('Primary key "' + primary_key + '" is not a variable of table "' + table
                                 + '" in meta data')

        if primary_key != self.data[table]['primary_key']:
            if self.data[table]['primary_key'] != '':
                old_key = self.data[table]['primary_key']
                for other in self.get_table_names():
                    if other == table:
                        continue
                    if old_key in self.get_foreign_keys(other):
                        self.remove_foreign_key(other, old_key)
                self.data[table]['variables'][old_key].variable_type = VariableType.Categorical
            self.data[table]['variables'][primary_key].variable_type = VariableType.PrimaryKey
            self.data[table]['primary_key'] = primary_key

    def add_foreign_key(self, table : str, foreign_table : str, foreign_key : str) -> None:
        """Adds a foreign key and its foreign origin table to a specified table. ``foreign_key`` must be a variable of
        ``table`` and a primary key of ``foreign_table``.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :param foreign_table: The name of the foreign table, i.e. its file name with '.csv' omitted
        :param foreign_key: The name of the foreign key, i.e. the column name
        :return:
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        if foreign_table not in self.data:
            raise AttributeError('Foreign table "' + foreign_table + '" not in meta data')
        if foreign_key in self.data[table]['foreign_keys']:
            raise AttributeError('Multiple assignment of foreign key "' + foreign_key + '" for table "' + table + '"')
        if self.data[foreign_table]['primary_key'] != foreign_key:
            raise AttributeError('Foreign key "' + foreign_key + '" is not primary key in table "'
                                 + foreign_table + '"')
        if foreign_key not in self.data[table]['variables']:
            raise AttributeError('Foreign key "' + foreign_key + '" is not a variable of table "' + table + '"')

        var_info = self.data[table]['variables'][foreign_key]
        var_info.variable_type = VariableType.ForeignKey
        if var_info.binning is not None:
            var_info.binning.should_bin = False
            var_info.binning.exclude_from_binning = None
        var_info.value_distribution = None
        if var_info.artifacts is not None:
            only_data_type_artifacts = []
            for artifact in var_info.artifacts:
                if var_info.cast_value_to_data_type(artifact) is None:
                    only_data_type_artifacts.append(artifact)
            var_info.artifacts = only_data_type_artifacts
        self.data[table]['foreign_keys'][foreign_key] = foreign_table

    def remove_foreign_key(self, table : str, foreign_key : str) -> None:
        """Removes a foreign key for a specified table. ``foreign_key`` must be a variable of ``table``.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :param foreign_key: The name of the foreign key, i.e. the column name
        :return:
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        if foreign_key not in self.data[table]['variables']:
            raise AttributeError('Foreign key "' + foreign_key + '" is not a variable of table "' + table + '"')
        if foreign_key not in self.data[table]['foreign_keys']:
            raise AttributeError('Foreign key "' + foreign_key + '" was not assigned for table "' + table + '"')

        var_info = self.data[table]['variables'][foreign_key]
        var_info.variable_type = VariableType.Categorical
        if var_info.binning is not None:
            var_info.binning.should_bin = False
            var_info.binning.exclude_from_binning = None
        del self.data[table]['foreign_keys'][foreign_key]

    def get_table_names(self) -> List[str]:
        """Retrieve all table name (file names with '.csv' omitted) of the metadata.

        :return: Returns the list of table names
        """
        return list(self.data.keys())

    def get_primary_key(self, table : str) -> str:
        """Retrieve the primary key of the table. Returns the empty string if not yet assigned.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :return: Returns the name of the primary key
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        return self.data[table]['primary_key']

    def has_primary_key(self, table : str) -> bool:
        """Checks if the table has a primary key assigned.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :return: Returns ``True`` if a primary key was assigned
        """
        return self.get_primary_key(table) != ''

    def get_foreign_keys(self, table) -> Dict[str, str]:
        """Retrieve all foreign keys of a table as a dictionary with the keys being the foreign keys and the values the
        foreign tables.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :return: Returns the foreign key/table dictionary
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        return self.data[table]["foreign_keys"]

    def get_label(self, table) -> str:
        """Returns the label of the table or the empty string if none was assigned.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :return: Returns the table label as string
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        return self.data[table]['label']

    def get_variable_names(self, table : str) -> List[str]:
        """Retrieves all variable names for a given table.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :return: Returns the list of retrieved variable names
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        return list(self.data[table]['variables'].keys())

    def get_variable(self, table : str, variable : str) -> VariableInfo:
        """Retrieves the information about a given variable for inspection or altering.

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :param variable: The name of the variable, i.e. the column name
        :return: Returns the variable information object
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        if variable not in self.data[table]['variables']:
            raise AttributeError('Variable "' + variable + '" is not a variable of table "' + table
                                 + '" in meta data')
        return self.data[table]['variables'][variable]

    def remove_variable(self, table: str, variable: str) -> None:
        """Delete the variable for the specified table from the metadata. If it is a primary key, foreign key
        references from other tables are deleted as well

        :param table: The name of the table, i.e. its file name with '.csv' omitted
        :param variable: The name of the variable, i.e. the column name
        """
        if table not in self.data:
            raise AttributeError('Table "' + table + '" not in meta data')
        if variable not in self.data[table]['variables']:
            raise AttributeError('Variable "' + variable + '" is not a variable of table "' + table
                                 + '" in meta data')
        if self.get_primary_key(table) == variable:
            for other in self.get_table_names():
                if other == table:
                    continue
                fks_to_delete = [fk for fk, ft in self.get_foreign_keys(other).items() if fk == variable and ft == table]
                for fk in fks_to_delete:
                    del self.data[other]["foreign_keys"][fk]
            self.data[table]['primary_key'] = ''
        del self.data[table]['variables'][variable]

    def has_artifacts(self) -> bool:
        """Check, if at least one variable has annotated artifacts

        :return: Returns ``True``, if at least one annotated artifact was found
        """
        for table in self.data:
            for variable in self.data[table]['variables']:
                var_info = self.data[table]['variables'][variable]
                if var_info.artifacts and len(var_info.artifacts) > 0:
                    return True
        return False

    def get_total_nof_variables(self) -> int:
        """Counts all variables in the metadata across all tables

        :return: Returns the count as an integer
        """
        result = 0
        for table in self.get_table_names():
            result += len(self.get_variable_names(table))
        return result