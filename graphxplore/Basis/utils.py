import csv
import re
import pathlib
import chardet
import os
import math
from typing import Dict, Any, Union, Optional, Tuple, Sequence, List

class BaseUtils:
    """This class contains utility functions.
    """
    @staticmethod
    def detect_file_encoding(file_path : str) -> str:
        """Reads the first 100k bytes from a file and guesses its encoding e.g., ASCII, UTF-8,...
        Can afterwards be used with `open(file_path, 'r', encoding=encoding)`. Uses the library chardet.

        :param file_path: The path to the file
        :return: Returns the guessed encoding
        """
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise AttributeError('Filepath "' + file_path + '" does not exist or is not a file')
        with open(file_path, 'rb') as file:
            raw_data = file.read(100000)
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            # ascii (without special characters) is subset of utf-8
            if encoding == 'ascii':
                encoding = 'utf-8'
            return encoding

    @staticmethod
    def load_csv_data(file_or_dir_path: str, delimiter: Optional[str] = None,
                      file_encoding : Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
        """Load table data from one CSV file or from all CSV files contained in a directory

        :param file_or_dir_path: Path to directory and file
        :param delimiter: CSV delimiter used for all files, inferred automatically if ``None`` is specified
        :param file_encoding: File encoding used for all files, inferred automatically if ``None`` is specified
        :return: Returns a dict with the filename without '.csv' extension as key and list of row dicts as table data
        """
        if not os.path.exists(file_or_dir_path):
            raise AttributeError('Filepath "' + file_or_dir_path + '" does not exist or is not a file')
        if os.path.isdir(file_or_dir_path):
            csv_files = {table[:-4] : str(pathlib.Path(os.path.join(file_or_dir_path, table)).resolve())
                         for table in os.listdir(file_or_dir_path) if table.endswith('.csv')}
            if len(csv_files) == 0:
                raise AttributeError('No CSV files found in directory "' + file_or_dir_path + '"')
        elif os.path.isfile(file_or_dir_path):
            if not file_or_dir_path.endswith('.csv'):
                raise AttributeError('No CSV file extension found in filepath "' + file_or_dir_path + '"')
            csv_files = {pathlib.Path(file_or_dir_path).stem : str(pathlib.Path(file_or_dir_path).resolve())}
        else:
            raise AttributeError('Not a valid filename or directory: "' + file_or_dir_path + '"')
        result = {}
        for table, file_path in csv_files.items():
            print('Loading data from table "' + table + '"')
            file_enc = file_encoding if file_encoding is not None else BaseUtils.detect_file_encoding(
                file_path)
            with open(file_path, encoding=file_enc) as file:
                if delimiter is None:
                    try:
                        dialect = csv.Sniffer().sniff(file.read(100000), delimiters=',;|\t ')
                        file.seek(0)
                        reader = csv.DictReader(file, dialect=dialect)
                    except csv.Error:
                        file.seek(0)
                        reader = csv.DictReader(file)
                else:
                    reader = csv.DictReader(file, delimiter=delimiter)
                result[table] = [row for row in reader]
        return result


    @staticmethod
    def check_csv_row(row: Dict[str, str], required_data : Dict[str, Any]):
        """Checks if all required fields are present in the CSV row and have the correct data type.

        :param row: The CSV row to check
        :param required_data: A dictionary of required field names and entry data types
        """
        for field, data_type in required_data.items():
            if field not in row:
                raise AttributeError('CSV row must contain the field "' + field + '"')
            try:
                data_type(row[field])
            except ValueError:
                raise AttributeError('CSV row entry for field "' + field + '" must be of type ' + data_type.__name__)

    @staticmethod
    def csv_row_string_to_list(row: Dict[str, str], row_key: str) -> Union[List[int], List[float], List[str]]:
        """Retrieves the value string for the key `row_key` from a CSV row, the value string should contain semicolons
         separating the individual property values. The string value is split and each entry is cast to string,
         integer or float.

        :param row: The CSV row as dictionary
        :param row_key: he key for the property in `row`
        :return: Returns the list of cast values
        """
        if row_key not in row:
            raise AttributeError('CSV row must contain the field "' + row_key + '"')
        split_string = row[row_key].split(';')
        if ':long' in row_key:
            try:
                return [int(entry) for entry in split_string]
            except ValueError:
                raise AttributeError('CSV row must contain integers seperated by semicolons in field "'
                                     + row_key + '"')
        elif ':double' in row_key:
            try:
                return [float(entry) for entry in split_string]
            except ValueError:
                raise AttributeError('CSV row must contain floats seperated by semicolons in field "'
                                     + row_key + '"')
        else:
            return split_string

    @staticmethod
    def combine_group_info(groups : List[str], group_size: Dict[str, int], pos_group: Optional[str],
                           neg_group: Optional[str]) -> List[str]:
        group_strings = []
        for group in groups:
            if group not in group_size:
                raise AttributeError('Group "' + group + '" not in group size dict')
            group_str = group + ' (' + str(group_size[group]) + ')'
            if pos_group == group:
                if neg_group == group:
                    raise AttributeError('Group "' + group + '" cannot be both positive and negative')
                group_str += '[+]'
            elif neg_group == group:
                group_str += '[-]'
            group_strings.append(group_str)
        return group_strings

    @staticmethod
    def extract_group_info_from_list(group_str_list: List[str]) -> Tuple[List[str], Dict[str, int], Optional[str], Optional[str]]:
        """Extracts group names, their sizes and optionally positive and negative group from a list of strings in the
        format "<group_name> (<group_size>)<[+] or [-] or blank>

        :param group_str_list: The string list containing all group data in the specified format
        :return: Returns all extracted data as a list of group names, dict of group sizes and positive and negative
            group if specified (or None)
        """
        groups = []
        group_size = {}
        pos_group = None
        neg_group = None
        for entry in group_str_list:
            split_idx = entry.rfind(' (')
            if split_idx == -1:
                raise AttributeError('CSV row group substring "' + entry + '" is invalid')
            group = entry[:split_idx]
            matches = re.findall(r'\d+', entry[split_idx:])
            if len(matches) != 1:
                raise AttributeError('CSV row group substring "' + entry + '" has invalid group size specifier')
            group_size[group] = int(matches[0])
            groups.append(group)
            if entry.endswith('[+]'):
                if pos_group is not None:
                    raise AttributeError('Two groups "' + pos_group + '" and "' + group
                                         + '" are specified as positive in group string list "'
                                         + '", "'.join(group_str_list) + '"')
                pos_group = group
            elif entry.endswith('[-]'):
                if neg_group is not None:
                    raise AttributeError('Two groups "' + neg_group + '" and "' + group
                                         + '" are specified as negative in group string "'
                                         + '", "'.join(group_str_list) + '"')
                neg_group = group
        return groups, group_size, pos_group, neg_group

    @staticmethod
    def extract_group_info_from_str(group_str : str) -> Tuple[List[str], Dict[str, int], Optional[str], Optional[str]]:
        """Extracts group names, their sizes and optionally positive and negative group from a string in the format
        "<group_name> (<group_size>)<[+] or [-] or blank>;<group_name> (<group_size>)<[+] or [-] or blank;...

        :param group_str: The string containing all group data in the specified format
        :return: Returns all extracted data as a list of group names, dict of group sizes and positive and negative
            group if specified (or None)
        """
        return BaseUtils.extract_group_info_from_list(group_str.split(';'))

    @staticmethod
    def calculate_mean(value_dist : Dict[Union[int, float], int]) -> Optional[float]:
        """Calculates the mean of a distribution dictionary with distribution values as key and counts as values of
        the dictionary. If the dictionary is empty `None` is returned.

        :param value_dist: The distribution
        :return: Returns the mean or `None` for empty distributions
        """
        if len(value_dist) == 0:
            return None
        acc_values = 0.0
        total_vals = 0
        for value, count in value_dist.items():
            acc_values += value * count
            total_vals += count
        return acc_values / total_vals

    @staticmethod
    def calculate_min_max(value_dist: Dict[Union[int, float], int]) -> Optional[Tuple[float, float]]:
        """Calculates the minimal and maximal value of a distribution dictionary with distribution values as key and
        counts as values of the dictionary. If the dictionary is empty `None` is returned.

        :param value_dist: The distribution
        :return: Returns the minimum and maximum or `None` for empty distributions
        """
        if len(value_dist) == 0:
            return None
        min_val = None
        max_val = None
        for value, count in value_dist.items():
            if min_val is None or min_val > value:
                min_val = value
            if max_val is None or max_val < value:
                max_val = value
        return min_val, max_val

    @staticmethod
    def calculate_std(value_dist: Dict[Union[int, float], int], mean : Optional[float] = None) -> Optional[float]:
        """Calculates the standard deviation of a distribution dictionary with distribution values as key and counts
        as values of the dictionary. If the dictionary is empty `None` is returned. A precalculated mean can be
        specified to speed up the calculation.

        :param value_dist: The distribution
        :param mean: The precalculated mean, defaults to None.
        :return: Returns the standard deviation or `None` for empty distributions
        """
        if len(value_dist) == 0:
            return None
        calc_mean = mean if mean is not None else BaseUtils.calculate_mean(value_dist)
        acc_var = 0.0
        total_vals = 0
        for value, count in value_dist.items():
            acc_var += count * (calc_mean - value) ** 2
            total_vals += count
        return math.sqrt(acc_var / total_vals)

    @staticmethod
    def calculate_median(value_dist : Dict[Union[int, float], int]) -> Optional[float]:
        """Calculates the median of a distribution dictionary with distribution values as key and counts as values of
        the dictionary. If the dictionary is empty `None` is returned.

        :param value_dist: The distribution
        :return: Returns the median or `None` for empty distributions
        """
        if len(value_dist) == 0:
            return None
        sorted_dist = sorted(value_dist.items())
        return BaseUtils.calculate_quartile_quintile_sorted_dist(sorted_dist, True, 2)

    @staticmethod
    def calculate_median_quartiles(value_dist: Dict[Union[int, float], int]) -> Optional[Tuple[float, Optional[float], Optional[float]]]:
        """Calculates the median and quartiles of a distribution dictionary with distribution values as key and counts
        as values of the dictionary. If the dictionary is empty `None` is returned. If the accumulated counts are less
        than four, quartiles are returned as ``None``.

        :param value_dist: The distribution
        :return: Returns the median, first quartile and third quartile, or `None` for empty distributions
        """
        if len(value_dist) == 0:
            return None
        sorted_dist = sorted(value_dist.items())
        median = BaseUtils.calculate_quartile_quintile_sorted_dist(sorted_dist, True, 2)
        first_quartile = BaseUtils.calculate_quartile_quintile_sorted_dist(sorted_dist, True, 1)
        third_quartile = BaseUtils.calculate_quartile_quintile_sorted_dist(sorted_dist, True, 3)
        return median, first_quartile, third_quartile

    @staticmethod
    def calculate_quartile_quintile_sorted_dist(sorted_dist : Sequence[Tuple[Union[int, float], int]],
                                                use_quartile : bool, quantile_id : int) -> Optional[float]:
        """Calculates quartiles or quintiles from a sorted distribution. If the distribution is empty, ```None`` is
        returned.

        :param sorted_dist: The distribution with pairs of values and counts sorted in ascending value order
        :param use_quartile: If ``True`` quartiles are calculate, else quintiles
        :param quantile_id: The identifier for the quartile. Must be 1, 2, or 3 for quartiles, or 1, 2, 3, 4 for quintiles
        :return: Returns the quartile, or `None` for empty distributions
        """
        if use_quartile and quantile_id not in [1, 2, 3]:
            raise AttributeError('Quartile ID must be 1, 2 or 3')
        if not use_quartile and quantile_id not in [1, 2, 3, 4]:
            raise AttributeError('Quintile ID must be 1, 2, 3 or 4')
        if len(sorted_dist) == 0:
            return None
        idx = 0
        count_sum = sum((entry[1] for entry in sorted_dist))
        accumulated_count = sorted_dist[idx][1]
        if use_quartile:
            multiplier = 4 if quantile_id == 1 else 2 if quantile_id == 2 else 4/3
            divisor = 2 if quantile_id == 2 else 4
        else:
            multiplier = 5 if quantile_id == 1 else 2.5 if quantile_id == 2 else 5/3 if quantile_id == 3 else 1.25
            divisor = 5
        while multiplier * accumulated_count < count_sum:
            idx += 1
            accumulated_count += sorted_dist[idx][1]
        # divisible
        if count_sum % divisor == 0:
            # at the border of two values
            if multiplier * accumulated_count == count_sum:
                return (sorted_dist[idx][0] + sorted_dist[idx + 1][0]) / 2
            else:
                return sorted_dist[idx][0]
        # not divisible
        else:
            return sorted_dist[idx][0]

    @staticmethod
    def count_lines_in_file(file_path : str) -> int:
        """Count lines in a text file

        :param file_path: The path to the text file
        :return: Returns the number of lines
        """
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise AttributeError('Filepath "' + file_path + '" does not exist or is not a file')
        with open(file_path, 'rb') as file:
            line_counter = 0
            raw_data = file.read(10000000)
            while raw_data:
                line_counter += raw_data.count(b'\n')
                raw_data = file.read(10000000)
            return line_counter

    @staticmethod
    def file_has_more_lines(file_path: str, threshold : int) -> bool:
        """Checks if a text file has more than ``threshold`` lines

        :param file_path: The path to the text file
        :param threshold: The threshold to be checked
        :return: Returns ``True`` if the file contains more lines
        """
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise AttributeError('Filepath "' + file_path + '" does not exist or is not a file')
        with open(file_path, 'rb') as file:
            line_counter = 0
            raw_data = file.read(100000)
            while raw_data and line_counter < threshold:
                line_counter += raw_data.count(b'\n')
                raw_data = file.read(100000)
            return line_counter > threshold