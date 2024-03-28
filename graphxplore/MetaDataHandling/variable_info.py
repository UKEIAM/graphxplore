import math
import re
from enum import Enum
from typing import List, Union, Any, Optional, Dict, Iterable
from dataclasses import dataclass, asdict
from graphxplore.Basis import BaseUtils

class VariableType(str, Enum):
    """The type of variable.
    """
    Categorical = 'Categorical'
    Metric = 'Metric'
    PrimaryKey = 'PrimaryKey'
    ForeignKey = 'ForeignKey'

class DataType(str, Enum):
    """A variable's data type.
    """
    String = 'String'
    Integer = 'Integer'
    Decimal = 'Decimal'

@dataclass
class BinningInfo:
    """This class contains information about the value binning of a metric variable into "low", "normal", and "high"
    bins. If desired lower and upper bounds for the reference range ("normal" bin) used in the binning process can be
    specified, or values can be excluded from binning such as artifacts.

    :param should_bin: Determines if the variable will be binned by the
        :class:`~graphxplore.GraphTranslation.GraphTranslator`
    :param exclude_from_binning: These values are excluded during the binning process, defaults to None
    :param ref_high: The optionally set upper bound of the reference range, defaults to None
    :param ref_low: The optionally set lower bound of the reference range, defaults to None
    """
    should_bin : bool
    exclude_from_binning : Optional[List[float]] = None
    ref_high : Optional[float] = None
    ref_low: Optional[float] = None

@dataclass
class MetricDistribution:
    """
    Value distribution for metric variables

    :param median: The median
    :param q1: The first quartile
    :param q3: The third quartile
    :param lower_fence: The maximum of the minimal value and ``q1`` - 1.5 interquartile range
    :param upper_fence: The minimum of the maximal value and ``q3`` + 1.5 interquartile range
    :param outliers: The list of values smaller than ``lower_fence`` or larger than ``upper_fence`` which are not
        annotated as artifacts
    :param missing_count: Count of cell values which are missing values
    :param artifact_count: Count of artifact cells
    """
    median : Union[int, float]
    q1 : Union[int, float]
    q3 : Union[int, float]
    lower_fence : Union[int, float]
    upper_fence : Union[int, float]
    outliers: List[Union[int, float]]
    missing_count : int
    artifact_count : int

@dataclass
class CategoricalDistribution:
    """
    Value distribution for categorical variables

    :param category_counts: Counts for the top 10 most frequent categories
    :param other_count: Accumulated count of categories not listed in ``category_counts``
    :param missing_count: Count of cell values which are missing values
    :param artifact_count: Count of artifact cells
    """
    category_counts : Dict[Union[str, int, float], int]
    other_count: int
    missing_count: int
    artifact_count: int

class ArtifactMode(str, Enum):
    """
    Here, you can choose the level to which GraphXplore should detect artifacts:

    - NoArtifacts: GraphXplore detects no artifacts
    - OnlyDataTypeMismatch: GraphXplore considers cell values artifacts which do not match the data type of the
      variable
    - DataTypeMismatchAndOutliers: In addition to data type mismatch artifacts, GraphXplore considers extreme
      outliers as  artifacts. For categorical variables where the top 10 most frequent categories account for at
      50% of the data, cell values which are not in the top 10 and appear only once are detected as artifacts.
      GraphXplore assumes these values to be typos. For metric variables, values which have  no other value within
      1.5 interquartile range, are considered artifacts
    """
    NoArtifacts = 'NoArtifacts'
    OnlyDataTypeMismatch = 'OnlyDataTypeMismatch'
    DataTypeMismatchAndOutliers = 'DataTypeMismatchAndOutliers'


@dataclass
class VariableInfo:
    """This class contains all information about a single variable.

    :param name: The name of the variable, i.e. the column name
    :param table: The name of the origin table, i.e. its file name with '.csv' omitted
    :param labels: One or multiple labels describing the variable
    :param variable_type: The type of variable
    :param data_type: The data type of the variable
    :param description: A description of the variable, e.g. containing units of measurement or SNOMED CT codes,
        defaults to None
    :param data_type_distribution: The percentage of different data types in the variable, defaults to None
    :param default_value: The optional default value of the variable, defaults to None
    :param value_distribution: Distribution of values depending on the variable type, defaults to None
    :param binning: The binning info of the variable, defaults to None
    :param artifacts: Potential artifacts existing for the variable, defaults to None
    :param reviewed: Variable information was reviewed, defaults to None
    """
    name : str
    table : str
    labels : List[str]
    variable_type : VariableType
    data_type : DataType
    description: Optional[str] = None
    data_type_distribution : Optional[Dict[DataType, float]] = None
    default_value : Optional[Union[str, int, float]] = None
    value_distribution : Optional[Union[MetricDistribution, CategoricalDistribution]] = None
    binning : Optional[BinningInfo] = None
    artifacts : Optional[List[str]] = None
    reviewed : Optional[bool] = None

    def add_label(self, label : str):
        """Add a label to the variable, e.g. describing its broad category such as "Laboratory".

        :param label: The label to add, must only contain letters, numbers, hyphens or underscores
        """
        if label in self.labels:
            raise AttributeError('Label "' + label + '" already assigned')
        if label == '':
            raise AttributeError('Label cannot be empty')
        if not re.match("^[A-Za-z0-9-_]+$", label):
            raise AttributeError('Label "' + label + '" should only contain letters, numbers, hyphens and underscores')
        self.labels.append(label)

    @staticmethod
    def from_dict(var_name : str, table : str, variable_dict : dict) -> 'VariableInfo':
        """Parses a :class:`VariableInfo` object from a dictionary.

        :param var_name: The name of the variable, i.e. the column name
        :param table: The name of the origin table, i.e. its file name with '.csv' omitted
        :param variable_dict: A dictionary containing all information about the variable
        :return: Returns the parsed object
        """
        name = VariableInfo.__check_dict_entry(var_name, 'name', variable_dict, str)
        if name != var_name:
            raise AttributeError('Variable name "' + name + '" in dictionary does not match variable "' + var_name
                                 + '"')
        table_from_dict = VariableInfo.__check_dict_entry(var_name, 'table', variable_dict, str)
        if table_from_dict != table:
            raise AttributeError('Origin table "' + table_from_dict + '" in dictionary for variable "' + name
                                 + '" does not match table "' + table + '"')
        labels = VariableInfo.__check_dict_entry(var_name, 'labels', variable_dict, list)
        variable_type = VariableInfo.__check_dict_entry(var_name, 'variable_type', variable_dict, (str, VariableType))
        if variable_type not in ['Categorical', 'Metric', 'PrimaryKey', 'ForeignKey']:
            raise AttributeError('Variable type "' + variable_type
                                 + '" invalid, must be "Categorical", "Metric", "PrimaryKey" or "ForeignKey"')
        variable_type = variable_type if isinstance(variable_type, VariableType) else VariableType[variable_type]
        data_type = VariableInfo.__check_dict_entry(var_name, 'data_type', variable_dict, (str, DataType))
        if data_type not in ['String', 'Integer', 'Decimal']:
            raise AttributeError('Data type "' + data_type
                                 + '" invalid, must be "String", "Integer" or "Decimal"')
        data_type = data_type if isinstance(data_type, DataType) else DataType[data_type]
        description = VariableInfo.__check_dict_entry(var_name, 'description', variable_dict, str, True)
        type_dist = VariableInfo.__check_dict_entry(var_name, 'data_type_distribution', variable_dict, dict, True)
        if type_dist is not None:
            converted_type_dist = {}
            for data_key, val in type_dist.items():
                if not isinstance(data_key, DataType) and data_key not in DataType.__members__:
                    raise AttributeError('In data type distribution the key "' + str(data_key)
                                         + '" was specified, but is not a valid data type')
                casted_val = VariableInfo.cast_value(val, DataType.Decimal)
                if casted_val is None:
                    raise AttributeError('In data type distribution the value "' + str(val)
                                         + '" was specified, but is not a decimal')
                converted_type_dist[DataType[data_key]] = casted_val
            type_dist = converted_type_dist
        default_value = VariableInfo.__check_dict_entry(var_name, 'default_value', variable_dict, (str, int, float),
                                                        True)
        if default_value is not None:
            casted_default_value = VariableInfo.cast_value(default_value, data_type)
            if casted_default_value is None:
                raise AttributeError('Default value "' + str(default_value) + '" is not of type ' + data_type)
            default_value = casted_default_value
        value_dist_dict = VariableInfo.__check_dict_entry(var_name, 'value_distribution', variable_dict, dict, True)
        if value_dist_dict is not None:
            cat_fields = {'category_counts' : dict, 'other_count' : int, 'missing_count' : int, 'artifact_count' : int}
            metric_fields = {'median' : (int, float), 'q1' : (int, float), 'q3' : (int, float),
                             'lower_fence' : (int, float), 'upper_fence' : (int, float), 'outliers' : list,
                             'missing_count' : int, 'artifact_count' : int}
            use_cat = True
            use_metric = True
            for field in cat_fields.keys():
                if field not in value_dist_dict:
                    use_cat = False
                    break
            if not use_cat:
                for field in metric_fields.keys():
                    if field not in value_dist_dict:
                        use_metric = False
                        break
            if not use_cat and not use_metric:
                raise AttributeError(
                    'Value distribution dict not recognized. For metric distributions these keys would be required: "'
                    + '" ,"'.join(metric_fields.keys()) + '". For categorical distributions these keys would be '
                                                          'required: "'
                    + '" ,"'.join(cat_fields.keys()) + '"')

            fields_to_check = cat_fields if use_cat else metric_fields
            value_dist_sub_dict = {}
            for key, class_type in fields_to_check.items():
                if not isinstance(value_dist_dict[key], class_type):
                    if isinstance(class_type, tuple):
                        type_string = ', '.join([single_type.__name__ for single_type in class_type])
                    else:
                        type_string = class_type.__name__
                    raise AttributeError('Value of key "' + key + '" in value distribution for variable "'
                                         + var_name + '" must be of type ' + type_string)
                value_dist_sub_dict[key] = value_dist_dict[key]
            if use_cat:
                value_distribution = CategoricalDistribution(**value_dist_sub_dict)
            else:
                value_distribution = MetricDistribution(**value_dist_sub_dict)
        else:
            value_distribution = None

        binning_dict = VariableInfo.__check_dict_entry(var_name, 'binning', variable_dict, dict, True)
        if binning_dict is not None:
            should_bin = VariableInfo.__check_dict_entry(var_name, 'should_bin', binning_dict, bool)
            exclude_from_binning = VariableInfo.__check_dict_entry(var_name, 'exclude_from_binning', binning_dict,
                                                                     list, True)
            if should_bin and data_type == DataType.String:
                raise AttributeError('Variable ' + var_name + ' is marked for binning, but has string type')
            ref_high = VariableInfo.__check_dict_entry(var_name, 'ref_high', binning_dict, float, True)
            ref_low = VariableInfo.__check_dict_entry(var_name, 'ref_low', binning_dict, float, True)
            if (ref_low is None) != (ref_high is None):
                raise AttributeError('For variable "' + var_name
                                     + '" both or none of reference low and reference high have to be set')
            if ref_low is not None and ref_low > ref_high:
                raise AttributeError('For variable "' + var_name + '" reference low "' + str(ref_low)
                                     + '" is larger than reference high "' + str(ref_high) + '"')
            bin_info = BinningInfo(should_bin, exclude_from_binning, ref_high, ref_low)
        else:
            bin_info = None

        artifact_list = VariableInfo.__check_dict_entry(var_name, 'artifacts', variable_dict, list, True)

        if 'reviewed' in variable_dict:
            reviewed = VariableInfo.__check_dict_entry(var_name, 'reviewed', variable_dict, bool, True)
        else:
            reviewed = None

        return VariableInfo(name=name, table=table, labels=labels, variable_type=variable_type,
                            data_type=data_type, description=description,
                            data_type_distribution=type_dist, default_value=default_value,
                            value_distribution=value_distribution, binning=bin_info,
                            artifacts=artifact_list, reviewed=reviewed)

    def to_dict(self) -> dict:
        """Converts the object to a dictionary.

        :return: Returns the generated dictionary
        """
        result = asdict(self)
        result['variable_type'] = self.variable_type.value
        result['data_type'] = self.data_type.value
        if self.data_type_distribution is not None:
            result['data_type_distribution'] = {data_type.value : frac
                                                for data_type, frac in self.data_type_distribution.items()}
        return result

    def cast_value_to_data_type(self, val_to_cast : Union[str, int, float]) -> Union[str, int, float, None]:
        """Casts a value to the data type of the variable. Returns `None` if the value could not be cast.

        :param val_to_cast: The value which should be cast
        :return: Returns the cast value
        """
        return self.cast_value(val_to_cast, self.data_type)

    @staticmethod
    def cast_value(val_to_cast : str, data_type : DataType) -> Union[str, int, float, None]:
        """Casts a value to the specified data type. Returns `None` if the value could not be cast.

        :param val_to_cast: The value which should be cast
        :param data_type: The data type to which the value should be cast
        :return: Returns the cast value
        """
        if data_type == DataType.Integer:
            try:
                return int(val_to_cast)
            except (ValueError, TypeError):
                return None
        if data_type == DataType.Decimal:
            try:
                return float(val_to_cast)
            except (ValueError, TypeError):
                return None
        return str(val_to_cast)

    def detect_artifacts_and_value_distribution(
            self, value_count_dict : Dict[str, int], artifact_mode : ArtifactMode = ArtifactMode.DataTypeMismatchAndOutliers,
            missing_vals : Iterable[Union[str, None]] = ('', 'NaN', 'Na', 'NA', 'NAN', 'nan', 'na')):
        """Calculates a value distribution based on the variable type. For categorical variables, a distribution with
        counts is calculated. For metric variables, data for a whisker plot is calculated. For primary and foreign keys
        no value distributions is derived. For more information check out :class:`MetricDistribution` and
        :class:`CategoricalDistribution`. Depending on ``artifact_mode``, artifacts are detected on the specified
        level. Pre-existing artifacts are preserved. For more information check out :class:`ArtifactMode`

        :param value_count_dict: The dictionary with all values (as string) and their occurrence count
        :param artifact_mode: Determines if artifacts should be detected and at what level. For further information
            check :class:`ArtifactMode`
        :param missing_vals: The list of possible missing values as string
        """
        detected_artifacts = set(self.artifacts) if self.artifacts is not None else set()
        cast_vals = {}
        artifact_count = 0
        missing_count = 0
        cast_val_orig_dict = {}

        # values that do not match the data type -> artifact
        for val, count in value_count_dict.items():
            if val is None or val in missing_vals:
                missing_count += count
                continue
            if val in detected_artifacts:
                artifact_count += count
                continue
            cast_val = self.cast_value_to_data_type(val)
            if cast_val is None:
                if artifact_mode != ArtifactMode.NoArtifacts:
                    detected_artifacts.add(val)
                    artifact_count += count
            else:
                cast_vals[cast_val] = count
                cast_val_orig_dict[cast_val] = val

        if self.variable_type == VariableType.Categorical:
            sorted_vals = sorted(cast_vals.items(), key=lambda  x: x[1], reverse=True)
            summed_count = sum(cast_vals.values())
            explicit_count = 0
            category_counts = {}
            top_ten_idx = min(len(sorted_vals), 10)
            for idx in range(top_ten_idx):
                cast_val, count = sorted_vals[idx]
                category_counts[cast_val_orig_dict[cast_val]] = count
                explicit_count += count
            # top 10 values with the highest account for at least 50% of data
            # -> values which appear only once and are not in top 10 -> artifacts
            if explicit_count >= 0.5 * summed_count:
                other_count = summed_count - explicit_count
                if artifact_mode == ArtifactMode.DataTypeMismatchAndOutliers and top_ten_idx < len(sorted_vals):
                    for cast_val, count in sorted_vals[top_ten_idx:]:
                        if count == 1:
                            detected_artifacts.add(cast_val_orig_dict[cast_val])
                            artifact_count += count
                            other_count -= count
                self.value_distribution = CategoricalDistribution(category_counts, other_count, missing_count,
                                                                  artifact_count)
            # top 10 values with the highest count are less than 50% of data -> no artifacts (apart wrong data type)
            else:
                self.value_distribution = None

        elif self.variable_type == VariableType.Metric:
            if self.data_type == DataType.String:
                raise AttributeError('Variable ' + self.name + ' is declared as "Metric", but is of type "String"')
            median, first_quartile, third_quartile = BaseUtils.calculate_median_quartiles(cast_vals)
            inter_quartile_range = third_quartile - first_quartile
            whisker_length = 1.5 * inter_quartile_range
            sorted_vals = sorted(cast_vals.keys())
            lower_fence = max(sorted_vals[0], first_quartile - whisker_length)
            upper_fence = min(sorted_vals[-1], third_quartile + whisker_length)
            outliers = []
            for idx in range(len(sorted_vals)):
                cast_val = sorted_vals[idx]
                # metric values have no other value within 1.5 x interquartile range -> artifact
                if artifact_mode == ArtifactMode.DataTypeMismatchAndOutliers:
                    has_close_neighbor = False
                    if idx > 0:
                        left_val = sorted_vals[idx - 1]
                        if math.fabs(cast_val - left_val) <= whisker_length:
                            has_close_neighbor = True
                    if not has_close_neighbor and idx < len(sorted_vals) - 1:
                        right_val = sorted_vals[idx + 1]
                        if math.fabs(right_val - cast_val) <= whisker_length:
                            has_close_neighbor = True
                    if not has_close_neighbor:
                        detected_artifacts.add(cast_val_orig_dict[cast_val])
                        artifact_count += cast_vals[cast_val]
                if ((cast_val < lower_fence or cast_val > upper_fence)
                        and cast_val_orig_dict[cast_val] not in detected_artifacts):
                    outliers.append(cast_val)
            self.value_distribution = MetricDistribution(median, first_quartile, third_quartile, lower_fence,
                                                         upper_fence, outliers, missing_count, artifact_count)

        if len(detected_artifacts) > 0:
            self.artifacts = sorted(detected_artifacts)
        else:
            self.artifacts = None

    @staticmethod
    def __check_dict_entry(var_name : str, dict_key : str, dict_to_check : dict, data_type : Union[Any, tuple],
                           none_valid : bool = False):
        """Checks if the key `dict_key` exists in the dictionary `dict_to_check` capturing information about the
        variable of name `var_name`. If the key exists, its value must be of type (or one of the types) `data_type`. If
        `none_valid` is `True` the method returns `None` if the key does not exist

        :param var_name: The name of the variable, i.e. the column name
        :param dict_key: The dictionary key that should exist
        :param dict_to_check: The dictionary that is checked
        :param data_type: The allowed data type(s) of its value
        :param none_valid: If `True`, None is returned if the key does not exist
        :return: Returns the value if valid or raises an exception
        """
        if dict_key not in dict_to_check:
            if none_valid:
                return None
        if dict_key not in dict_to_check\
                or not (isinstance(dict_to_check[dict_key], data_type)
                        or (none_valid and dict_to_check[dict_key] is None)):
            if isinstance(data_type, tuple):
                type_string = ', '.join([single_type.__name__ for single_type in data_type])
            else:
                type_string = data_type.__name__
            error_string = 'Dictionary for variable "' + var_name\
                           + '" does not contain an entry "' + dict_key + '" of type ' + type_string
            if none_valid:
                error_string += ', None would also be valid'
            raise AttributeError(error_string)
        return dict_to_check[dict_key]