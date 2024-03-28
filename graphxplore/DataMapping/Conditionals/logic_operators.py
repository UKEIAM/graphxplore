import collections
from enum import Enum
from typing import Union, Iterable, Tuple, Dict, List, Optional
from graphxplore.MetaDataHandling import DataType, VariableInfo
from ..data_structure_transformer import SourceDataLine
from ..data_aggregator import AggregatorType, AggregatorParser

class LogicOperator:
    """This is the abstract parent class of all conditionals for a :class:`~graphxplore.DataMapping.MappingCase`.
    Each logic operator checks the validity of a given line of source data based on the described conditional
    """
    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        """Returns the source tables and variables needed by the conditional for its validity check

        :return: Returns the required data as a dictionary
        """
        raise NotImplementedError('Never call the parent class')

    def valid(self, source_data : SourceDataLine) -> bool:
        """Checks if the conditions of the logic operator are given by a line of source data.

        :param source_data: The line of source data
        :return: Returns ``True`` if the conditional is met, ``False`` otherwise
        """
        raise NotImplementedError('Never call the parent class')

    def __str__(self) -> str:
        raise NotImplementedError('Never call the parent class')

class AndOperator(LogicOperator):
    """This logic operator checks if all of its sub-operators are valid.

    :param sub_operators: The sub-operators
    """
    def __init__(self, sub_operators : Iterable[LogicOperator]):
        self.sub_operators = list(sub_operators)

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        result = collections.defaultdict(set)
        for operator in self.sub_operators:
            sub_result = operator.get_required_data()
            for table, variables in sub_result.items():
                result[table].update(variables)
        return {table : list(variables) for table, variables in result.items()}

    def valid(self, source_data : SourceDataLine) -> bool:
        for operator in self.sub_operators:
            if not operator.valid(source_data):
                return False
        return True

    def __str__(self) -> str:
        return '(' + ' AND '.join([str(operator) for operator in self.sub_operators]) + ')'

class OrOperator(LogicOperator):
    """This logic operator checks if any of its sub-operators is valid.

    :param sub_operators: The sub-operators
    """
    def __init__(self, sub_operators: Iterable[LogicOperator]):
        self.sub_operators = sub_operators

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        result = collections.defaultdict(set)
        for operator in self.sub_operators:
            sub_result = operator.get_required_data()
            for table, variables in sub_result.items():
                result[table].update(variables)
        return {table : list(variables) for table, variables in result.items()}

    def valid(self, source_data : SourceDataLine) -> bool:
        for operator in self.sub_operators:
            if operator.valid(source_data):
                return True
        return False

    def __str__(self) -> str:
        return '(' + ' OR '.join([str(operator) for operator in self.sub_operators]) + ')'

class NegatedOperator(LogicOperator):
    """This logic operator negates an input operator ``pos_operator``, i.e. it checks if ``pos_operator.valid()``
    evaluates to ``False``

    :param pos_operator: The operator to negate
    """
    def __init__(self, pos_operator: LogicOperator):
        self.pos_operator = pos_operator

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        return self.pos_operator.get_required_data()

    def valid(self, source_data : SourceDataLine) -> bool:
        return not self.pos_operator.valid(source_data)

    def __str__(self) -> str:
        return '(NOT ' + str(self.pos_operator) + ')'

class AlwaysTrueOperator(LogicOperator):
    """This logic operator always evaluates to ``True``. Consequently, its
    :class:`~graphxplore.DataMapping.MappingCase` is always triggered, when checked. As a result, it can be used as a
    default.
    """
    def valid(self, source_data : SourceDataLine) -> bool:
        return True

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        return {}

    def __str__(self) -> str:
        return '(TRUE)'

class AtomicOperator(LogicOperator):
    """This abstract class and all its children check the value of a single source variable in a line of source data.

    :param table: The table of the source variable
    :param variable: The name of the source variable
    :param data_type: The data type the value of the source variable should have
    """
    def __init__(self, table : str, variable : str, data_type : DataType):
        self.table = table
        self.variable = variable
        self.data_type = data_type

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        return {self.table: [(self.variable, ((self.aggregator, self.data_type)
                                              if isinstance(self, AggregatorOperator) else None))]}

    def valid(self, source_data : SourceDataLine) -> bool:
        raise NotImplementedError('Never call the parent class')

    def common_prefix(self) -> str:
        """Generates the common prefix of all atomic logic operators containing the variable, its data type and its
        origin table.

        :return: Returns the prefix string
        """
        return 'VARIABLE ' + self.variable + ' OF TYPE ' + self.data_type + ' IN TABLE ' + self.table

    def common_atomic_str(self, inner : str) -> str:
        """Wraps an inner string with the prefix and brackets common to all atomic logic operators.

        :param inner: The inner part of the string which depends on the type of logic operator
        :return: Returns the generated str
        """
        return ('(' + self.common_prefix() + ' ' + inner
                + ')')

    @staticmethod
    def from_string(input_str: str) -> Optional['AtomicOperator']:
        """Parses an input string and generates the operator if the string is valid

        :param input_str: The string to parse
        :return: Returns the parsed operator or ``None`` if ``input_str`` is invalid for this type of
            operator
        """
        raise NotImplementedError('Never call the parent class')

    @staticmethod
    def extract_common_atomic(input_str : str) -> Optional[Tuple[str, str, DataType]]:
        """Extracts source table, variable and data type from a string if it is valid.

        :param input_str: The input string
        :return: Returns the source table, variable and data type
        """
        if not input_str.startswith('VARIABLE '):
            return None
        idx = input_str.find(' OF TYPE ')
        if idx == -1:
            return None
        variable = input_str[0:idx].replace('VARIABLE ', '', 1)
        rest = input_str[idx:].replace(' OF TYPE ', '', 1)
        idx = rest.find(' IN TABLE ')
        if idx == -1:
            return None
        data_type = rest[0:idx]
        if data_type not in DataType.__members__:
            return None
        rest = rest[idx:].replace(' IN TABLE ', '', 1)
        idx = rest.find(' ')
        if idx == -1:
            return None
        table = rest[0:idx]
        return table, variable, DataType[data_type]

    def __str__(self):
        raise NotImplementedError('Never call the parent class')

class InListOperator(AtomicOperator):
    """This logic operator checks if the value for a given source variable has the correct data type and is contained
    in a list of values. Can be combined with :class:`NegatedOperator` to form a "black list check".

    :param table: The source table of the variable
    :param variable: The source variable
    :param data_type: The desired data type of the variable's value
    :param white_list: The list of acceptable values, gets converted so string values
    """
    def __init__(self, table : str, variable : str, data_type : DataType, white_list : Iterable):
        super().__init__(table, variable, data_type)
        self.ordered_white_list = [str(entry) for entry in white_list]
        self.white_list = set(self.ordered_white_list)

    def valid(self, source_data : SourceDataLine) -> bool:
        raw_val = source_data.get_singular_value(self.table, self.variable)
        if raw_val is None:
            return False
        casted_val = VariableInfo.cast_value(raw_val, self.data_type)
        if casted_val is None:
            return False
        return str(raw_val) in self.white_list

    @staticmethod
    def from_string(input_str : str) -> Optional['InListOperator']:
        outer = AtomicOperator.extract_common_atomic(input_str)
        if outer is None:
            return None
        table, variable, data_type = outer
        idx = input_str.find('IN [')
        if idx == -1:
            return None
        if input_str[-1] != ']':
            return None
        substring = input_str[idx:-1].replace('IN [', '', 1)
        white_list = substring.split(', ')
        white_list = [entry.strip('"') for entry in white_list]
        return InListOperator(table, variable, data_type, white_list)

    def __str__(self) -> str:
        inner = 'IN [' + ', '.join([entry if ' ' not in entry else '"' + entry + '"'
                                    for entry in self.ordered_white_list]) + ']'
        return self.common_atomic_str(inner)

class StringOperatorType(str, Enum):
    """The type of logic operator on string variables
    """
    Equals = 'IS'
    Contains = 'CONTAINS'

class StringOperator(AtomicOperator):
    """This logic operator performs string comparisons between the value of a single source variable and ``value``.

    :param table: The source table of the variable
    :param variable: The source variable
    :param value: The value for comparison
    :param compare: The type of string comparison
    """
    def __init__(self, table : str, variable : str, value : str, compare : StringOperatorType):
        super().__init__(table, variable, DataType.String)
        self.value = value
        self.compare = compare

    def valid(self, source_data : SourceDataLine) -> bool:
        source_val = source_data.get_singular_value(self.table, self.variable)
        if source_val is None:
            return False
        return StringOperator.check_value(source_val, self.value, self.compare)

    @staticmethod
    def check_value(val_to_check : str, to_check_against : str, compare : StringOperatorType) -> bool:
        """Checks the validity of ``val_to_check``

        :param val_to_check: The value to check the validity for
        :param to_check_against: The base value to check against
        :param compare: The type of comparison
        :return: Returns ``True`` if ``val_to_check`` is valid, else ``False``
        """
        if compare == StringOperatorType.Equals:
            return val_to_check == to_check_against
        if compare == StringOperatorType.Contains:
            return to_check_against in val_to_check
        raise NotImplemented('String operator type not implemented')

    @staticmethod
    def from_string(input_str: str) -> Optional['StringOperator']:
        outer = AtomicOperator.extract_common_atomic(input_str)
        if outer is None:
            return None
        table, variable, data_type = outer
        if data_type != DataType.String:
            return None
        literals = input_str.split(maxsplit=9)
        if len(literals) != 10:
            return None
        compare = literals[-2]
        value = literals[-1]
        if compare not in StringOperatorType._value2member_map_:
            return None
        if not value.startswith('"') or not value.endswith('"'):
            return None
        value = value[1:-1]
        return StringOperator(table, variable, value, StringOperatorType(compare))

    def __str__(self) -> str:
        inner = self.compare + ' ' + '"' + self.value + '"'
        return self.common_atomic_str(inner)

class MetricOperatorType(str, Enum):
    """The type of logic operator on metric or categorical variables of numeric type
    """
    Equals = '=='
    Smaller = '<'
    Larger = '>'
    SmallerOrEqual = '<='
    LargerOrEqual = '>='

class MetricOperator(AtomicOperator):
    """This logic operator performs metric comparisons between the value of a single source variable and ``value``.

    :param table: The source table of the variable
    :param variable: The source variable
    :param value: The value for comparison
    :param compare: The type of metric comparison
    """
    def __init__(self, table : str, variable : str, value : Union[int, float], data_type : DataType,
                 compare : MetricOperatorType):
        super().__init__(table, variable, data_type)
        self.value = value
        self.compare = compare

    def valid(self, source_data : SourceDataLine) -> bool:
        raw_val = source_data.get_singular_value(self.table, self.variable)
        if raw_val is None:
            return False
        casted_val = VariableInfo.cast_value(raw_val, self.data_type)
        if casted_val is None:
            return False
        return MetricOperator.check_value(casted_val, self.value, self.compare)

    @staticmethod
    def check_value(val_to_check: Union[int, float], to_check_against: Union[int, float],
                    compare: MetricOperatorType) -> bool:
        """Checks the validity of ``val_to_check``

        :param val_to_check: The value to check the validity for
        :param to_check_against: The base value to check against
        :param compare: The type of comparison
        :return: Returns ``True`` if ``val_to_check`` is valid, else ``False``
        """
        if compare == MetricOperatorType.Equals:
            return val_to_check == to_check_against
        if compare == MetricOperatorType.Smaller:
            return val_to_check < to_check_against
        if compare == MetricOperatorType.SmallerOrEqual:
            return val_to_check <= to_check_against
        if compare == MetricOperatorType.Larger:
            return val_to_check > to_check_against
        if compare == MetricOperatorType.LargerOrEqual:
            return val_to_check >= to_check_against
        raise NotImplemented('Metric operator type not implemented')

    @staticmethod
    def from_string(input_str: str) -> Optional['MetricOperator']:
        outer = AtomicOperator.extract_common_atomic(input_str)
        if outer is None:
            return None
        table, variable, data_type = outer
        if data_type != DataType.Integer and data_type != DataType.Decimal:
            return None
        literals = input_str.split()
        if len(literals) != 10:
            return None
        compare = literals[-2]
        value = literals[-1]
        if compare not in MetricOperatorType._value2member_map_:
            return None
        casted_val = VariableInfo.cast_value(value, data_type)
        if casted_val is None:
            return None
        return MetricOperator(table, variable, casted_val, data_type, MetricOperatorType(compare))

    def __str__(self) -> str:
        inner = self.compare + ' ' + str(self.value)
        return self.common_atomic_str(inner)

class AggregatorOperator(AtomicOperator):
    """This logic operator checks aggregated data of a specific table, variable and data type for a primary key value.
    It can be used to check time series for certain events. E.g., if at least one blood pressure measurements was above
    a certain threshold or all doctor's notes mentioned a certain precondition.

    :param table: The table of origin of the variable to check
    :param variable: The name of variable to check
    :param value: The value to check the aggregated data against
    :param data_type: Only values of this type will be aggregated
    :param aggregator: The type of aggregation
    :param compare: The comparison between the aggregated data and ``value``. Must match ``aggregator``. E.g. minimum,
        maximum or average calculations must be compared with :class:`MetricOperatorType` objects.
        ``AggregatorType.List`` must be used with ``StringOperatorType.Contains`` and ``AggregatorType.Concatenate``
        with :class:`StringOperatorType` objects
    """
    def __init__(self, table : str, variable : str, value : Union[str, int, float], data_type : DataType,
                 aggregator : AggregatorType, compare : Union[StringOperatorType, MetricOperatorType]):
        super().__init__(table, variable, data_type)
        # check if aggregator type is valid for variable data type
        AggregatorParser.check_compatibility(table, variable, data_type, aggregator)
        # check if aggregator type and comparison operator are compatible
        aggregated_data_type = AggregatorParser.get_aggregated_data_type(aggregator)
        if aggregated_data_type == DataType.Decimal or aggregated_data_type == DataType.Integer:
            if not isinstance(compare, MetricOperatorType):
                raise AttributeError('Aggregator type "' + aggregator
                                     + '" of variable "' + variable + '" in table "' + table
                                     + '" can only be combined with a metric operator type. Possible types are: "'
                                     + '", "'.join(MetricOperatorType._value2member_map_.keys()) + '"')
        elif aggregator == AggregatorType.List:
            if compare != StringOperatorType.Contains:
                raise AttributeError('Aggregator type "' + AggregatorType.List
                                     + '" of variable "' + variable + '" in table "' + table
                                     + '" must be combined with operator type "'
                                     + StringOperatorType.Contains + '"')
        elif aggregator == AggregatorType.Concatenate:
            if not isinstance(compare, StringOperatorType):
                raise AttributeError('Aggregator type "' + AggregatorType.Concatenate
                                     + '" of variable "' + variable + '" in table "' + table
                                     + '" must be combined with a string operator type. Possible types are: "'
                                     + '", "'.join(StringOperatorType._value2member_map_.keys()) + '"')
        # check if comparison operator and value to check against are compatible
        if (type(value) == str) != isinstance(compare, StringOperatorType):
            raise AttributeError('Variable "' + variable + '" in table "' + table
                                 + '" has mismatch of operator type "' + compare
                                 + '" and value type to compare with ' + value.__class__.__name__)
        self.value = value
        self.compare = compare
        self.aggregator = aggregator

    def valid(self, source_data : SourceDataLine) -> bool:
        # value already casted, if nothing was aggregated, None is returned
        aggregated_value = source_data.aggregated_data.get_variable_aggregation(self.table, self.variable,
                                                                                self.data_type, self.aggregator)
        if aggregated_value is None:
            return False
        if self.aggregator == AggregatorType.List:
            return str(self.value) in aggregated_value
        if isinstance(self.compare, StringOperatorType):
            return StringOperator.check_value(aggregated_value, self.value, self.compare)
        return MetricOperator.check_value(aggregated_value, self.value, self.compare)

    def __str__(self) -> str:
        return ('(' + AggregatorParser.to_str(self.table, self.variable, self.data_type, self.aggregator) + ' '
                + self.compare + ' '
                + (str(self.value) if isinstance(self.compare, MetricOperatorType) else '"' + self.value + '"') + ')')

    @staticmethod
    def from_string(input_str: str) -> Optional['AggregatorOperator']:
        aggregator_parsed = AggregatorParser.from_string(input_str)
        if aggregator_parsed is None:
            return None
        table, variable, data_type, aggregator = aggregator_parsed
        idx = input_str.find('TABLE')
        if idx == -1:
            return None
        sub_str = input_str[idx:]
        literals = sub_str.split(maxsplit=3)[2:]
        if len(literals) != 2:
            return None
        compare = literals[0]
        value = literals[1]
        if compare in StringOperatorType._value2member_map_:
            if not value.startswith('"') or not value.endswith('"'):
                return None
            value = value[1:-1]
            compare = StringOperatorType(compare)
        elif compare in MetricOperatorType._value2member_map_:
            casted_value = VariableInfo.cast_value(value, DataType.Integer)
            if casted_value is None:
                casted_value = VariableInfo.cast_value(value, DataType.Decimal)
                if casted_value is None:
                    return None
            value = casted_value
            compare = MetricOperatorType(compare)
        else:
            return None
        return AggregatorOperator(table, variable, value, data_type, aggregator, compare)

class LogicOperatorParser:
    """This class parses conditional strings and extracts the represented :class:`LogicOperator`
    """
    @staticmethod
    def from_string(input_str: str) -> LogicOperator:
        """Parses a string and returns the generated :class:`LogicOperator` or raises an exception of the string is
        invalid.

        :param input_str: The input string
        :return: Returns the generated operator
        """
        return LogicOperatorParser.__from_string_rec(input_str, input_str)

    @staticmethod
    def __from_string_rec(current : str, input_str : str) -> LogicOperator:
        """Recursively parses parts of an input string by detecting brackets and identifying sub-strings for parsing.

        :param current: The current substring
        :param input_str: The full input string
        :return: Returns the generated logic operator
        """
        if not current.startswith('('):
            raise AttributeError('Logic sub operator string must start with opening parenthesis: ' + current
                                 + ', total string was: ' + input_str)
        if not current.endswith(')'):
            raise AttributeError('Logic sub operator string must end with closing parenthesis: ' + current
                                 + ', total string was: ' + input_str)
        if len(current) < 3:
            raise AttributeError('Logic sub operator contains "()": ' + current
                                 + ', total string was: ' + input_str)
        # outer parenthesis removed
        substring = current[1:-1]
        # found atomic operator
        if '(' not in substring:
            if ')' in substring:
                raise ('Logic sub operator string has too many closing parenthesis: ' + current
                                 + ', total string was: ' + input_str)
            if substring == 'TRUE':
                return AlwaysTrueOperator()
            operator = InListOperator.from_string(substring)
            if operator is not None:
                return operator
            operator = StringOperator.from_string(substring)
            if operator is not None:
                return operator
            operator = MetricOperator.from_string(substring)
            if operator is not None:
                return operator
            operator = AggregatorOperator.from_string(substring)
            if operator is not None:
                return operator
            raise AttributeError('Logic atomic operator string is invalid: ' + current
                                 + ', total string was: ' + input_str)

        # found negation
        elif substring.startswith('NOT '):
            pos_substring = substring[4:]
            pos_operator = LogicOperatorParser.__from_string_rec(pos_substring, input_str)
            return NegatedOperator(pos_operator)

        # found composition
        else:
            if not substring.startswith('('):
                raise AttributeError('Logic sub composite operator string must start with opening parenthesis: ' + substring
                                     + ', total string was: ' + input_str)
            # find sub operators
            return LogicOperatorParser.resolve_composition(substring, input_str)
    @staticmethod
    def resolve_composition(substring : str, input_str : str) -> Union[AndOperator, OrOperator]:
        """Decompose and/or composition into sub operators

        :param substring: The current substring
        :param input_str: The full input string
        :return: Returns the and/or logic operator
        """
        sub_operator_strings = []
        counter = 0
        starting_idx = None
        composition_type = None
        for idx, char in enumerate(substring):
            if char == '(':
                counter += 1
                if counter == 1:
                    starting_idx = idx
            elif char == ')':
                counter -= 1
                if counter == 0:
                    # found closing parenthesis
                    if starting_idx is None:
                        raise AttributeError(
                            'Logic sub composite operator string does not have enough opening parenthesis: ' + substring
                            + ', total string was: ' + input_str)
                    sub_operator_strings.append(substring[starting_idx:idx + 1])
                    # check composition type
                    if idx < len(substring) - 1:
                        comp_start = substring[idx + 1:]
                        if comp_start.startswith(' AND '):
                            if composition_type is None:
                                composition_type = 'and'
                            elif composition_type == 'or':
                                raise AttributeError(
                                    'Logic sub composite operator string cannot have "AND" and "OR" as composition: '
                                    + substring + ', total string was: ' + input_str)
                        elif comp_start.startswith(' OR '):
                            if composition_type is None:
                                composition_type = 'or'
                            elif composition_type == 'and':
                                raise AttributeError(
                                    'Logic sub composite operator string cannot have "AND" and "OR" as composition: '
                                    + substring + ', total string was: ' + input_str)
                        else:
                            raise AttributeError(
                                'Logic sub composite operator string must have "AND" or "OR" as composition: ' + substring
                                + ', total string was: ' + input_str)

        sub_operators = [LogicOperatorParser.__from_string_rec(composite_sub, input_str)
                         for composite_sub in sub_operator_strings]
        if composition_type == 'and':
            return AndOperator(sub_operators)
        else:
            return OrOperator(sub_operators)