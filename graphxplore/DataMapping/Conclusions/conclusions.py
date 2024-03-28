from typing import Union, Dict, List, Optional, Tuple
from graphxplore.MetaDataHandling.meta_data import  VariableInfo, DataType
from ..data_aggregator import AggregatorType, AggregatorParser
from ..data_structure_transformer import SourceDataLine

class Conclusion:
    """This is the abstract parent class of all conclusions of :class:`~graphxplore.DataMapping.MappingCase` objects.

    :param target_data_type: The data type of the target variable
    """
    def __init__(self, target_data_type: DataType):
        self.target_data_type = target_data_type

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        """Returns the required source tables and variables for the conclusion to operate.

        :return: Returns a dictionary of required source tables and variables of the table
        """
        raise NotImplementedError('Never call the parent class')

    def get_return(self, source_data: SourceDataLine) -> Optional[Union[str, int, float]]:
        """Triggers the conclusion on the source data and generates the return value for the target data based on
        ``source_data``.

        :param source_data: The line of source data
        :return: Returns the value of the target variable, or None
        """
        raise NotImplemented('Never call parent class')

    def __str__(self):
        raise NotImplemented('Never call parent class')

    @staticmethod
    def from_string(input_str : str) -> Optional['Conclusion']:
        """Generates a :class:`Conclusion` object from an input string if it is valid

        :param input_str: The input string
        :return: Returns the generated conclusion or ``None``, if the string was invalid
        """
        raise NotImplemented('Never call parent class')

class CopyConclusion(Conclusion):
    """This conclusion copies the value of a source variable from a given line source data, if the value fits the data
    type of the target variable.

    :param target_data_type: The data type of the target variable
    :param origin_table: The source table of the variable to copy
    :param var_to_copy: the name of the source variable to copy
    """
    def __init__(self, target_data_type: DataType, origin_table : str, var_to_copy : str):
        super().__init__(target_data_type)
        self.origin_table = origin_table
        self.var_to_copy = var_to_copy

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        return {self.origin_table : [(self.var_to_copy, None)]}

    def get_return(self, source_data: SourceDataLine) -> Optional[Union[str, int, float]]:
        raw_copy_val = source_data.get_singular_value(self.origin_table, self.var_to_copy)
        if raw_copy_val is None:
            return None
        return VariableInfo.cast_value(raw_copy_val, self.target_data_type)

    def __str__(self):
        return ('COPY VARIABLE ' + self.var_to_copy + ' IN TABLE ' + self.origin_table + ' IF TYPE IS '
                + self.target_data_type)

    @staticmethod
    def from_string(input_str: str) -> Optional['CopyConclusion']:
        if not input_str.startswith('COPY VARIABLE '):
            return None
        rest = input_str.replace('COPY VARIABLE ', '', 1)
        idx = rest.find(' IN TABLE ')
        if idx == -1:
            return None
        var = rest[:idx]
        rest = rest[idx:].replace(' IN TABLE ', '', 1)
        idx = rest.find(' IF TYPE IS ')
        if idx == -1:
            return None
        table = rest[:idx]
        data_type = rest[idx:].replace(' IF TYPE IS ', '', 1)
        if data_type not in DataType.__members__:
            return None
        return CopyConclusion(DataType[data_type], table, var)

class FixedReturnConclusion(Conclusion):
    """This conclusion returns a fixed value casted to the data type of the target variable

    :param target_data_type: The data type of the target variable
    :param return_val: The fixed return value
    """
    def __init__(self, target_data_type: DataType, return_val: Union[str, int, float, None]):
        super().__init__(target_data_type)
        self.return_value = VariableInfo.cast_value(return_val, self.target_data_type)
        if self.return_value is None:
            raise AttributeError('Fixed return does not match target data type')

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        return {}

    def get_return(self, source_data: SourceDataLine) -> Optional[Union[str, int, float]]:
        return self.return_value

    def __str__(self):
        return 'RETURN ' + str(self.return_value) + ' OF TYPE ' + self.target_data_type

    @staticmethod
    def from_string(input_str: str) -> Optional['FixedReturnConclusion']:
        if not input_str.startswith('RETURN '):
            return None
        rest = input_str.replace('RETURN ', '', 1)
        idx = rest.find(' OF TYPE ')
        if idx == -1:
            return None
        return_val = rest[:idx]
        data_type = rest[idx:].replace(' OF TYPE ', '', 1)
        if data_type not in DataType.__members__:
            return None
        return FixedReturnConclusion(DataType[data_type], return_val)

class AggregateConclusion(Conclusion):
    """This conclusion returns the aggregation of all data of a specific table, variable and data type for a primary
    key value. It can e.g. be used to extract minimal, maximal or average values from time series or check if a patient
    was diagnosed with a certain condition at least once.

    :param source_data_type: Only values of this type will be aggregated
    :param origin_table: The table of origin for the variable
    :param var_to_aggregate: The name of the variable
    :param aggregator: The type of data aggregation
    """
    def __init__(self, source_data_type: DataType, origin_table: str, var_to_aggregate: str,
                 aggregator : AggregatorType):
        """Constructor method
        """
        if aggregator == AggregatorType.List:
            raise AttributeError('Aggregator type "' + AggregatorType.List + '" for variable "' + var_to_aggregate
                                 + '" of table "' + origin_table + '" not allowed for conclusion')
        # check if aggregator type is valid for variable data type
        AggregatorParser.check_compatibility(origin_table, var_to_aggregate, source_data_type, aggregator,
                                             list_aggregation_allowed=False)
        # check if aggregator type and comparison operator are compatible
        aggregated_data_type = AggregatorParser.get_aggregated_data_type(aggregator)
        super().__init__(aggregated_data_type)
        self.source_data_type = source_data_type
        self.origin_table = origin_table
        self.var_to_aggregate = var_to_aggregate
        self.aggregator = aggregator

    def get_required_data(self) -> Dict[str, List[Tuple[str, Optional[Tuple[AggregatorType, DataType]]]]]:
        return {self.origin_table: [(self.var_to_aggregate, (self.aggregator, self.source_data_type))]}

    def get_return(self, source_data: SourceDataLine) -> Optional[Union[str, int, float]]:
        return source_data.aggregated_data.get_variable_aggregation(self.origin_table, self.var_to_aggregate,
                                                                    self.source_data_type, self.aggregator)

    def __str__(self):
        return AggregatorParser.to_str(self.origin_table, self.var_to_aggregate, self.source_data_type, self.aggregator)

    @staticmethod
    def from_string(input_str : str) -> Optional['AggregateConclusion']:
        aggregator_parsed = AggregatorParser.from_string(input_str)
        if aggregator_parsed is None:
            return None
        table, variable, data_type, aggregator = aggregator_parsed
        return AggregateConclusion(data_type, table, variable, aggregator)

class ConclusionParser:

    @staticmethod
    def from_string(input_str : str) -> Conclusion:
        """Parse a conclusion from string

        :param input_str: The string to be parsed
        :return: Returns the parsed conclusion or raises an exception
        """
        conclusion = CopyConclusion.from_string(input_str)
        if conclusion is None:
            conclusion = FixedReturnConclusion.from_string(input_str)
        if conclusion is None:
            conclusion = AggregateConclusion.from_string(input_str)
        if conclusion is None:
            raise AttributeError('The input string ' + input_str + ' is not a valid conclusion')
        return conclusion