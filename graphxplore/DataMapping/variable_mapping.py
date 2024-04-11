import collections
from typing import Dict, Union, List, Optional
from dataclasses import dataclass
from .data_structure_transformer import SourceDataLine
from .Conditionals import LogicOperator, LogicOperatorParser
from .Conclusions import Conclusion, ConclusionParser

@dataclass
class MappingCase:
    """This class contains a conditional clause that is checked against the source data and a conclusion generating the
    target data. It resembles the atomic part of a data mapping process. If the condition is met, the conclusion is
    processed.

    :param conditional: The condition that evaluates to ``True`` or ``False``
    :param conclusion: The conclusion returning the target data, if ``conditional`` evaluates to ``True`` on
        the input data
    """
    conditional : LogicOperator
    conclusion : Conclusion

    def to_dict(self) -> Dict[str, str]:
        """Returns a dictionary contained the data of the object

        :return: Returns the dictionary
        """
        return {
            'if': str(self.conditional),
            'then' : str(self.conclusion)
        }

    @staticmethod
    def from_dict(input_dict : dict) -> 'MappingCase':
        """Generates a :class:`MappingCase` object from a dictionary.

        :param input_dict: The input dictionary
        :return: Returns the generated :class:`MappingCase` object
        """
        if 'if' not in input_dict:
            raise AttributeError('Dictionary for mapping case must have an if-clause')
        conditional = LogicOperatorParser.from_string(input_dict['if'])
        if 'then' not in input_dict:
            raise AttributeError('Dictionary for mapping case must have a then-clause')
        conclusion = ConclusionParser.from_string(input_dict['then'])
        return MappingCase(conditional, conclusion)

class VariableMapping:
    """This class contains all data required for the data mapping of one target variable.

    :param target_table: The table of the target variable
    :param target_variable: The name of the target variable
    :param cases: The mapping cases (input order sensitive)
    """
    def __init__(self, target_table: str, target_variable : str, cases: List[MappingCase]):
        """Constructor method
        """
        self.target_table = target_table
        self.target_variable = target_variable
        self.cases = []
        self.sources = collections.defaultdict(set)
        for case in cases:
            self.add_case(case)

    def __getitem__(self, source_data : SourceDataLine) -> Optional[Union[str, int, float]]:
        """The :class:`MappingCase` objects specified in ``self.cases`` are processed in
        the given input order until one condition is met, the conclusion of the case is returned. If no condition is
        met, None gets returned.

        :param source_data: The source data flattened by a :class:`DataFlattener` object
        :return: Returns the return value of the first conclusion with a met conditional, or None
        """
        for case in self.cases:
            if case.conditional.valid(source_data):
                return case.conclusion.get_return(source_data)
        return None

    def to_dict(self) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Converts the object to a dictionary.

        :return: Returns the object's dictionary
        """
        return {
            'target_table' : self.target_table,
            'target_variable' : self.target_variable,
            'cases' : [case.to_dict() for case in self.cases]
        }

    @staticmethod
    def from_dict(input_dict : Dict[str, Union[str, List[Dict[str, str]]]]) -> 'VariableMapping':
        """Generates a :class:`VariableMapping` object from a dictionary.

        :param input_dict:
        :return: Returns the generated :class:`VariableMapping` object
        """
        target_table = VariableMapping.__read_entry_from_dict(input_dict, 'target_table', str)
        target_variable = VariableMapping.__read_entry_from_dict(input_dict, 'target_variable', str)
        case_dicts = VariableMapping.__read_entry_from_dict(input_dict, 'cases', list)
        cases = []
        for case_dict in case_dicts:
            if not isinstance(case_dict, dict):
                raise AttributeError('Variable mapping dictionary entry "cases" must be a list of dicts')
            cases.append(MappingCase.from_dict(case_dict))
        return VariableMapping(target_table=target_table, target_variable=target_variable, cases=cases)

    @staticmethod
    def __read_entry_from_dict(input_dict : Dict[str, Union[str, list]], key : str,
                               class_type : type) -> Union[str, list]:
        """Checks if ``key`` is in ``input_dict`` and if its value has the correct type ``class_type``.

        :param input_dict: The input dictionary
        :param key: The dictionary key
        :param class_type:
        :return: Returns the value, if it has the correct type. Raises exception otherwise
        """
        if not isinstance(input_dict, dict):
            raise AttributeError('Input for variable mapping must be a dictionary')
        if key not in input_dict:
            raise AttributeError('Variable mapping dictionary must contain key "' + key + '"')
        if not isinstance(input_dict[key], class_type):
            raise AttributeError('Variable mapping dictionary entry "' + key + '" must be of type "'
                                 + class_type.__name__ + '"')
        return input_dict[key]

    def add_case(self, case : MappingCase) -> None:
        """Adds a mapping case to the mapping at the last position. The required tables and variables are added to
        ``self.sources``

        :param case: The mapping case to add
        """
        self.cases.append(case)
        for table, variables in case.conditional.get_required_data().items():
            self.sources[table].update(variables)
        for table, variables in case.conclusion.get_required_data().items():
            self.sources[table].update(variables)

    def remove_case(self, case_idx : int) -> None:
        """Removes a mapping case by index. ``self.sources`` is updated as well

        :param case_idx: The index of the case to remove
        """
        if case_idx >= len(self.cases):
            raise AttributeError('Index ' + str(case_idx) + ' to large for removal. Only '
                                 + str(len(self.cases)) + ' mapping cases exist')
        self.sources = collections.defaultdict(set)
        for idx in range(len(self.cases)):
            if idx == case_idx:
                continue
            case = self.cases[idx]
            for table, variables in case.conditional.get_required_data().items():
                self.sources[table].update(variables)
            for table, variables in case.conclusion.get_required_data().items():
                self.sources[table].update(variables)
        del self.cases[case_idx]