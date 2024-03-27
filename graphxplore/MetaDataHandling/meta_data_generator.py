import collections
import itertools
from typing import Union, Optional, List, Dict, Iterable
from graphxplore.Basis import RelationalDataIODevice
from .variable_info import BinningInfo, VariableType, DataType, ArtifactMode
from .meta_data import MetaData

class MetaDataGenerator:
    """This class extracts metadata information from CSV files. It detects primary keys and foreign key relations
    between tables. Additionally, :class:`VariableInfo` objects are inferred for all columns of all CSV files. The
    result is a :class:`MetaData` object.

    :param csv_data: The input data as CSV files either as directory path containing the CSV files or as
        dictionary of table name and table data as list of dictionaries per row
    :param artifact_mode: Determines if artifacts should be detected and at what level. For further information check
        :class:`ArtifactMode`
    :param missing_vals: These characters indicate missing values, defaults to empty string, None and variations of
        "NaN" and "Na"
    :param nof_read_lines: Maximum number of lines read from each CSV file to gather metadata, defaults to 1 million
    :param str_len_free_text: Strings with at least this number of characters are considered free text and the
        containing variable is unfavored as primary key. Defaults to 300.
    :param binning_threshold: Metric variables with more distinct values are marked for binning, defaults to 20
    :param categorical_threshold: Variables with at most this number of distinct values are considered categorical,
        defaults to 20
    :param file_encoding: The file encoding of the CSV files (ascii, utf-8,...) in chardet definition.
        Is guessed if not specified. Only used when CSV data is read from a directory, defaults to None
    """

    def __init__(self, csv_data: Union[str, Dict[str, List[Dict[str, str]]]],
                 artifact_mode : ArtifactMode = ArtifactMode.DataTypeMismatchAndOutliers,
                 missing_vals : Iterable[Union[str, None]] = ('', 'NaN', 'Na', 'NA', 'NAN', 'nan', 'na'),
                 nof_read_lines : int = 1000000, str_len_free_text : int = 300, binning_threshold : int = 20,
                 categorical_threshold : int = 20, file_encoding : Optional[str] = None):
        """Constructor method
        """
        tables = RelationalDataIODevice.get_available_table_names(csv_data)
        self.result = MetaData(tables)
        self.csv_data = csv_data
        self.artifact_mode = artifact_mode
        self.missing_vals = missing_vals
        self.file_encoding = file_encoding
        self.nof_read_lines = nof_read_lines
        self.str_len_free_text = str_len_free_text
        self.binning_threshold = binning_threshold
        self.categorical_threshold = categorical_threshold

    def gather_meta_data(self) -> MetaData:
        """Extracts variables and primary/foreign key relations between CSV files. Each CSV MUST contain a column with
        unique entries and no empty cells. Among these, a primary key is selected prioritizing integer columns.
        Additionally, :class:`VariableInfo` objects are inferred for all columns of all CSV files. Artifacts are
        detected, if specified by ``artifact_mode``. For more information checkout :class:`ArtifactMode`

        :return: Returns the gathered metadata
        """
        self.extract_variable_infos()

        print('Assigning foreign keys')

        self.assign_foreign_keys()

        return self.result

    def extract_variable_infos(self) -> None:
        """Extracts all information about variables contained in CSVs of the source directory and detects primary keys.
        Artifacts are detected, if specified by ``artifact_mode``. For more information checkout :class:`ArtifactMode`
        """
        tables_without_primary = []

        for table in self.result.get_table_names():
            print('Extracting variable information from table ' + table)
            self.result.assign_label(table, label=table)
            data = self.__extract_data(table)
            primary_key = self.__get_primary_key(data)
            if primary_key == "":
                tables_without_primary.append(table)
            for variable in data.keys():
                var_info = self.result.add_variable(table, variable)
                var_info.data_type = data[variable]['data_type']
                var_info.data_type_distribution = data[variable]['data_type_dist']
                if variable == primary_key:
                    self.result.assign_primary_key(table, primary_key)
                    print('Assigned ' + primary_key + ' as primary key to table ' + table)
                    continue
                val_count_dict = data[variable]['value_dist']
                if (var_info.data_type in [DataType.Decimal, DataType.Integer]
                        and var_info.variable_type not in [VariableType.PrimaryKey, VariableType.ForeignKey]):
                    non_missing_vals = {val : count for val, count in val_count_dict.items()
                                        if val not in self.missing_vals}
                    non_missing_unique_count = sum(non_missing_vals.values())
                    if len(non_missing_vals) > self.categorical_threshold:
                        var_info.variable_type = VariableType.Metric
                    if non_missing_unique_count > self.binning_threshold:
                        var_info.binning = BinningInfo(should_bin=True, exclude_from_binning=[])
                    else:
                        var_info.binning = BinningInfo(should_bin=False, exclude_from_binning=None)
                else:
                    var_info.binning = BinningInfo(should_bin=False, exclude_from_binning=None)

                if var_info.variable_type not in [VariableType.PrimaryKey, VariableType.ForeignKey]:
                    var_info.detect_artifacts_and_value_distribution(val_count_dict, artifact_mode=self.artifact_mode,
                                                                     missing_vals=self.missing_vals)

            data.clear()

        if len(tables_without_primary) != 0:
            table_str = 'table' if len(tables_without_primary) == 1 else 'tables'
            print('No primary key found for ' + table_str + ' "' + '", "'.join(tables_without_primary) + '"')

    def __get_primary_key(self, data: dict) -> str:
        """Processes all columns of a CSV and tries to find a primary key which contains only unique cell values and no
        empty values. The hint dict is used (if specified) and integer columns are preferred over string or float.

        :param data: The variable data that was extracted before
        :return: Returns the name of the found primary key column or an empty string if none was found
        """
        integer_candidates = []
        other_candidates = []
        backup_candidates = []

        for var_name, var_dict in data.items():
            # cell values must be unique and should not contain missing values
            if not var_dict['values_are_unique'] or var_dict['contains_missing_vals']:
                continue
            if  var_dict['contains_freetext']:
                backup_candidates.append(var_name)
                continue
            (integer_candidates if var_dict['data_type'] == DataType.Integer else other_candidates).append(var_name)

        all_candidates = integer_candidates + other_candidates + backup_candidates

        if len(all_candidates) == 0:
            return ""
        return all_candidates[0]

    def assign_foreign_keys(self) -> None:
        """Assigns foreign keys by detecting occurrences of primary keys in other tables.
        """
        for table, foreign_table in itertools.permutations(self.result.get_table_names(), 2):
            for variable in self.result.get_variable_names(table):
                if variable == self.result.get_primary_key(table):
                    continue
                if self.result.get_primary_key(foreign_table) != variable:
                    continue
                if variable in self.result.get_foreign_keys(table):
                    print('Variable "' + variable + '" was assigned as foreign key in table "' + table
                          + '" with foreign table "' + self.result.get_foreign_keys(table)[variable]
                          + '", but could also be assigned with foreign table "' + foreign_table + '"')
                    continue
                self.result.add_foreign_key(table, foreign_table, variable)
                var_info = self.result.get_variable(table, variable)
                var_info.value_distribution = None
                var_info.binning = BinningInfo(should_bin=False, exclude_from_binning=None)

    def __extract_data(self, table: str) -> dict:
        """Extract data for one CSV table. Either by loading a maximum of ``self.nof_read_lines``
        (1 million by default) lines from a CSV file, or retrieving the pre-read data from a dictionary. Data types are
        inferred and check for empty as well as freetext cells is done.

        :param table: Name of the CSV table
        :return: Returns a dictionary of the columns with the generated data
        """
        with RelationalDataIODevice(self.csv_data, table, file_encoding=self.file_encoding) as reader:
            data = {}
            for column in reader.get_header():
                data[column] = {
                    'column_name' : column,
                    'data_type' : DataType.String,
                    'contains_freetext' : False,
                    'contains_missing_vals' : False,
                    'value_dist' : collections.defaultdict(int),
                    'nof_non_missing' : 0,
                    'data_type_dist' : {DataType.String : 0, DataType.Integer : 0, DataType.Decimal : 0},
                    'values_are_unique' : True}
            counter = 0
            for line in reader:
                for column, val in line.items():
                    data[column]['value_dist'][val] += 1
                    if val is None or val in self.missing_vals:
                        data[column]['contains_missing_vals'] = True
                    else:
                        data[column]['nof_non_missing'] += 1
                        datatype = self.__infer_cell_datatype(val)
                        data[column]['data_type_dist'][datatype] += 1
                        # cell value not seen before
                        if data[column]['value_dist'][val] == 1:
                            if not data[column]['contains_freetext'] and datatype == DataType.String:
                                if len(val) > self.str_len_free_text or "\n" in val:
                                    data[column]['contains_freetext'] = True
                        else:
                            data[column]['values_are_unique'] = False

                counter += 1
                if counter == self.nof_read_lines:
                    break
            self.__infer_table_datatypes(data)
            return data

    @staticmethod
    def __infer_cell_datatype(val: str) -> DataType:
        """Infers the data type of the current cell with the following hierarchy of specificity/preference:
        'Integer', 'Float', 'String'.

        :param val: The cell value
        :return: Returns the inferred cell data type
        """
        # data type int or not set yet
        # try to cast to int
        try:
            int(val)
            return DataType.Integer
        except (ValueError, TypeError):
            # try to cast to float
            try:
                float(val)
                return DataType.Decimal
            except (ValueError, TypeError):
                return DataType.String

    @staticmethod
    def __infer_table_datatypes(table_data: dict) -> None:
        """Infers the data type for each column by checking the distribution of data types of unique cell values.

        :param table_data: The data dictionary for the table
        """
        for column, column_data in table_data.items():
            nof_values = column_data['nof_non_missing']
            if nof_values > 0:
                for data_type, count in column_data['data_type_dist'].items():
                    column_data['data_type_dist'][data_type] = round(count/nof_values, 4)
            column_data['data_type'] = MetaDataGenerator.__infer_column_datatype(column_data['data_type_dist'])

    @staticmethod
    def __infer_column_datatype(type_dict: dict) -> DataType:
        """Checks the distribution of data types for a column. If more than 5% are strings, the whole column is assigned
        'String'. Same concept with lower priority for decimal numbers. Otherwise, the column is assigned 'Integer',
        which is the most specific data type.

        :param type_dict: The data type distribution
        :return: Returns the column data type
        """
        string_share = type_dict[DataType.String]
        if string_share > 0.05:
            return DataType.String
        float_share = type_dict[DataType.Decimal]
        if float_share > 0.05:
            return DataType.Decimal
        return DataType.Integer



