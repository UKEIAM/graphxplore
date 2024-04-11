import math
import re
from dataclasses import dataclass
from typing import Union, Optional, List, Tuple, Dict, Any
from enum import Enum
from ..graph_classes import Graph, GraphType
from ..utils import BaseUtils
from graphxplore.Basis.BaseGraph.base_classes import (BinBoundInfo, BaseLabels, BaseNode, BaseEdge, NodeDataType,
                                                      BaseNodeType, BaseEdgeType)

class AttributeAssociationGraph(Graph):
    """This is the graph holding :class:`AttributeAssociationNode` and :class:`AttributeAssociationEdge` objects.
    It captures statistical measurements about the occurrence of attributes within one or multiple groups of primary
    keys, as well as the conditional relations between attributes within these groups.

    :param nodes: The list of nodes
    :param edges: The list of edges
    """
    def __init__(self, nodes: Optional[List['AttributeAssociationNode']] = None,
                 edges: Optional[List['AttributeAssociationEdge']] = None):
        super().__init__(GraphType.AttributeAssociation, nodes, edges)

class FrequencyLabel(str, Enum):
    """Describes how frequent the property associated with a :class:`AttributeAssociationNode` appears in one or at least of
    multiple groups of primary keys.
    """
    Infrequent = 'Infrequent'
    Frequent = 'Frequent'
    HighlyFrequent = 'HighlyFrequent'

class DistinctionLabel(str, Enum):
    """Describes how much the relative attribute shares differ between the groups (if multiple groups exist).
    """
    HighlyInverse = 'HighlyInverse'
    Inverse = 'Inverse'
    Unrelated = 'Unrelated'
    Related = 'Related'
    HighlyRelated = 'HighlyRelated'

@dataclass
class AttributeAssociationLabels(BaseLabels):
    """These labels describe :class:`AttributeAssociationNode` objects and inherit from
    :class:`~graphxplore.Basis.BaseGraph.BaseLabels`.

    :param membership_labels: One or more labels describing the membership of the node into categories. The origin table
        should always be one label
    :param node_type: The type of node
    :param frequency_label: Describes how frequent the attribute appears in one or at least of multiple groups of
        primary keys
    :param distinction_label: Describes the difference and quotient in frequencies between primary key groups
    """
    def __init__(self, membership_labels : Tuple[str, ...], node_type : BaseNodeType,
                 frequency_label : Optional[FrequencyLabel] = None,
                 distinction_label : Optional[DistinctionLabel] = None):
        """Constructor method
        """
        super().__init__(membership_labels, node_type)
        self.frequency_label = frequency_label
        self.distinction_label = distinction_label

    @staticmethod
    def from_label_list(label_list : List[str]) -> 'AttributeAssociationLabels':
        """Generate a :class:`AttributeAssociationLabels` object from a list of strings. The single values should be
        seperated by semicolons and the :class:`~graphxplore.Basis.BaseGraph.BaseNodeType` label should appear last.
        Raises an exception if parsing failed.

        :param label_list: The input list from which the object is parsed
        :return: Returns the parsed object
        """
        if len(label_list) < 2:
            raise AttributeError('The label string should contain at least one label for the table or other '
                                 'affiliation and the node type as the last element')
        freq_label = None
        dist_label = None
        type_label = None
        mem_labels = []
        for label_str in label_list:
            if label_str in BaseNodeType.__members__:
                type_label = BaseNodeType(label_str)
            elif label_str in FrequencyLabel.__members__:
                freq_label = FrequencyLabel(label_str)
            elif label_str in DistinctionLabel.__members__:
                dist_label = DistinctionLabel(label_str)
            else:
                mem_labels.append(label_str)
        if type_label is None:
            raise AttributeError('One entry of the label list must describe the node type with one of: "'
                                 + '", "'.join(BaseNodeType.__members__) + '"')
        return AttributeAssociationLabels(membership_labels=tuple(mem_labels), node_type=type_label,
                                          frequency_label=freq_label, distinction_label=dist_label)
    @staticmethod
    def from_label_string(label_string: str) -> 'AttributeAssociationLabels':
        """Generate a :class:`AttributeAssociationLabels` object from a label string. The single values should be
        seperated by semicolons and the :class:`~graphxplore.Basis.BaseGraph.BaseNodeType` label should appear last. Raises an
        exception if parsing failed.

        :param label_string: The input string from which the object is parsed
        :return: Returns the parsed object
        """
        label_list = label_string.split(';')
        if len(label_list) < 2:
            raise AttributeError('Label string "' + label_string
                                 + '" is invalid, it should contain at least one label for the table or other '
                                   'affiliation and the node type as the last element')
        return AttributeAssociationLabels.from_label_list(label_list)

    def to_label_string(self) -> str:
        """Converts the object to a string. The individual labels are concatenated by semicolons, the
        :class:`FrequencyLabel` appears last.

        :return: Returns the converted string
        """
        return_string = super().to_label_string()
        if self.distinction_label is not None:
            return_string += ';' + self.distinction_label
        if self.frequency_label is not None:
            return_string += ';' + self.frequency_label
        return return_string

class AttributeAssociationNode(BaseNode):
    """This class contains the information of a (and inherits from) :class:`~graphxplore.Basis.BaseGraph.BaseNode` of type
    ``BaseNodeType.Attribute`` or ``BaseNodeType.AttributeBin``. In addition, it captures several statistical traits of
    the node's attribute within one or multiple groups of primary keys: Its absolute count, its prevalence, and the
    ratio of group members with a missing value for the variable ``name``. Moreover, if multiple groups are defined,
    the absolute difference and ratio of prevalence is calculated. If ``positive_group`` and ``negative_group`` are
    specified, the difference and ratio between their prevalence values is calculated. Else, between the maximum and
    minimum prevalence

    :param node_id: The internal Neo4J ID of the :class:`~graphxplore.Basis.BaseGraph.BaseNode`. Used for identity
        checks. As a result, nodes can only be compared if originating from the same
        :class:`~graphxplore.Basis.BaseGraph.BaseGraph`
    :param labels: The labels of the :class:`BaseNode` and potentially a :class:`FrequencyLabel` and
        :class:`DistinctionLabel`
    :param name: The name of the :class:`~graphxplore.Basis.BaseGraph.BaseNode`
    :param val: The value of the :class:`~graphxplore.Basis.BaseGraph.BaseNode`
    :param groups: The name of the groups
    :param desc: The description of the :class:`~graphxplore.Basis.BaseGraph.BaseNode`
    :param bin_info: The binning info of the :class:`~graphxplore.Basis.BaseGraph.BaseNode`
    :param positive_group: The name of the positive group (e.g. the disease cohort) or ``None``
    :param negative_group: The name of the negative group (e.g. the control cohort) or ``None``
    :param group_size: The number of group members. Will be initialized
        with 0 for each group if None
    :param count: The absolute counts of group members having this attribute. Will be initialized
        with 0 for each group if None
    :param missing: The ratio of group members with a missing value for variable ``name``. Will be initialized with 0.0
        for each group if None
    :param prevalence: The count divided by the number group members not having a missing value
        for the variable `name`. Will be initialized with 0.0 for each group if None
    :param prevalence_difference: The absolute difference between the prevalence of the ``positive_group`` and
        ``negative_group`` if defined, or between the maximum and minimum prevalence. Defaults to NaN
    :param prevalence_ratio: The larger divided by the smaller prevalence of the ``positive_group`` and
        ``negative_group`` if defined, or quotient between the maximum and minimum prevalence. Defaults to Nan
    """
    def __init__(self, node_id: int, labels: AttributeAssociationLabels, name: str, val: Union[str, int, float],
                 groups : List[str], desc: str = 'NaN', bin_info: Optional[BinBoundInfo] = None,
                 positive_group : Optional[str] = None, negative_group : Optional[str] = None,
                 group_size : Optional[Dict[str, int]] = None,
                 count : Optional[Dict[str, int]] = None, missing : Optional[Dict[str, float]] = None,
                 prevalence : Optional[Dict[str, float]] = None, prevalence_difference : float = math.nan,
                 prevalence_ratio : float = math.nan):
        """Constructor method
        """
        super().__init__(node_id, labels, name, val, desc, bin_info)
        self.labels = labels
        if len(groups) == 0:
            raise AttributeError('You have to define at least one group')
        for group in groups:
            if not re.match("^[A-Za-z0-9-_]+$", group):
                raise AttributeError(
                    'Group "' + group + '" should only contain letters, numbers, hyphens and underscores')
        self.groups = groups
        if positive_group is not None and negative_group is not None and positive_group == negative_group:
            raise AttributeError('Positive and negative group cannot be identical')
        if (positive_group is None) != (negative_group is None):
            raise AttributeError('Either both or none of positive and negative group have be specified')
        if positive_group is not None and positive_group not in self.groups:
            raise AttributeError('Positive group "' + positive_group + '" not in list of groups')
        if negative_group is not None and negative_group not in self.groups:
            raise AttributeError('Negative group "' + negative_group + '" not in list of groups')
        self.negative_group = negative_group
        self.positive_group = positive_group
        if group_size is not None:
            for group in self.groups:
                if group not in group_size:
                    raise AttributeError('Group size not specified for group "' + group + '"')
        self.group_size = group_size or {group : 0 for group in self.groups}
        if count is not None:
            for group in self.groups:
                if group not in count:
                    raise AttributeError('Count not specified for group "' + group + '"')
        self.count = count or {group : 0 for group in self.groups}
        if missing is not None:
            for group in self.groups:
                if group not in missing:
                    raise AttributeError('Missing value ratio not specified for group "' + group + '"')
        self.missing = missing or {group : 0.0 for group in self.groups}
        if prevalence is not None:
            for group in self.groups:
                if group not in prevalence:
                    raise AttributeError('Prevalence not specified for group "' + group + '"')
        self.prevalence = prevalence or {group : 0.0 for group in self.groups}
        self.prevalence_difference = prevalence_difference
        self.prevalence_ratio = prevalence_ratio
        self.graph_type = GraphType.AttributeAssociation

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        return self.node_id

    @staticmethod
    def get_csv_header(data_type: NodeDataType) -> List[str]:
        return BaseNode.get_csv_header(data_type) + ["groups[]", "count:long[]",
                                                     "missing:double[]", "prevalence:double[]",
                                                     "prevalence_difference:double", "prevalence_ratio:double"]

    @staticmethod
    def check_csv_row(row: Dict[str, str]) -> None:
        BaseNode.check_csv_row(row)
        BaseUtils.check_csv_row(row, {
            "groups[]" : str, "count:long[]" : str, "missing:double[]": str, "prevalence:double[]" : str,
            "prevalence_difference:double": float, "prevalence_ratio:double": float})

    @staticmethod
    def from_csv_row(row: Dict[str, str]) -> 'AttributeAssociationNode':
        casted_value, bin_info = BaseNode._get_value_and_bin_info_from_csv_row(row)
        AttributeAssociationNode.check_csv_row(row)
        groups, group_size, pos_group, neg_group = BaseUtils.extract_group_info_from_str(row['groups[]'])
        count = dict(zip(groups, BaseUtils.csv_row_string_to_list(row, 'count:long[]')))
        missing = dict(zip(groups, BaseUtils.csv_row_string_to_list(row, 'missing:double[]')))
        prevalence = dict(zip(groups, BaseUtils.csv_row_string_to_list(row, 'prevalence:double[]')))
        return AttributeAssociationNode(node_id=int(row[':ID']),
                                        labels=AttributeAssociationLabels.from_label_string(row[':LABEL']),
                                        name=row['name'], val=casted_value, groups=groups, desc=row['description'],
                                        bin_info=bin_info, positive_group=pos_group, negative_group=neg_group,
                                        group_size=group_size, count=count, missing=missing, prevalence=prevalence,
                                        prevalence_difference=float(row['prevalence_difference:double']),
                                        prevalence_ratio=float(row['prevalence_ratio:double']))

    def __convert_to_list(self, param_name : str):
        param_dict = getattr(self, param_name)
        return [param_dict[entry] for entry in self.groups]

    def __convert_to_str(self, param_name):
        return ';'.join((str(val) for val in self.__convert_to_list(param_name)))

    def to_csv_row(self) -> List[Union[str, int, float]]:
        return super().to_csv_row() + [
            ';'.join(BaseUtils.combine_group_info(
                self.groups, self.group_size, self.positive_group, self.negative_group)),
            self.__convert_to_str('count'),
            self.__convert_to_str('missing'),
            self.__convert_to_str('prevalence'),
            self.prevalence_difference,
            self.prevalence_ratio]

    def data_for_cypher_write_query(self) -> Tuple[List[str], Dict[str, Any]]:
        """Returns labels and parameter dictionary for a Cypher MERGE statement to insert the node into a Neo4J
        database.

        :return: Returns the data for the Cypher statement as a pair of label list and parameter dictionary
        """
        labels, params = super().data_for_cypher_write_query()

        params['groups'] = BaseUtils.combine_group_info(
            self.groups, self.group_size, self.positive_group, self.negative_group)
        params['count'] = self.__convert_to_list('count')
        params['missing'] = self.__convert_to_list('missing')
        params['prevalence'] = self.__convert_to_list('prevalence')
        params['prevalence_difference'] = self.prevalence_difference
        params['prevalence_ratio'] = self.prevalence_ratio
        return labels, params

class AttributeAssociationEdgeType(str, Enum):
    """The type of edge, specifying the degree of conditional relationship between the source and target node.
    """
    UNASSIGNED = 'UNASSIGNED'
    LOW_RELATION = 'LOW_RELATION'
    MEDIUM_RELATION = 'MEDIUM_RELATION'
    HIGH_RELATION = 'HIGH_RELATION'

class AttributeAssociationEdge(BaseEdge):
    """This class describes the conditional relationship between the attributes of two
    :class:`AttributeAssociationNode` objects. It contains statistical parameters for the absolute co-occurrence and the
    conditional prevalence of the target attribute given the source attribute. Additionally, the difference and ratio
    of the conditional prevalence and the prevalence of the target node are contained. This way, the
    influence of the added condition of the source attribute is expressed. These statistical measurements are
    stored for one or multiple groups of primary keys. Based on the maximum difference and ratio, the edge is
    assigned a type reflecting the degree of the conditional relationship.

    :param source: The ID of the source :class:`AttributeAssociationNode`
    :param target: The ID of the target :class:`AttributeAssociationNode`
    :param edge_type: The type of edge describing the degree of conditional implication
    :param positive_group: The name of the positive group (e.g. the disease cohort) or ``None``
    :param negative_group: The name of the negative group (e.g. the control cohort) or ``None``
    :param group_size: The number of group members. Will be initialized
        with 0 for each group if None
    :param co_occurrence: The absolute count of group members having both the source and target attribute.
        Specified for each group. Will be initialized with 0 for each group if None
    :param conditional_prevalence: The co-occurrence divided by absolute count of the source attribute, resulting in the
        conditional prevalence of the target attribute given the source attribute. Specified for each group. Will be
        initialized with 0.0 for each group if None
    :param conditional_increase: The conditional prevalence minus the prevalence of the target node. Specified for each
        group. Might be negative. Will be initialized with 0.0 for each group if None
    :param increase_ratio: The conditional prevalence divided by the prevalence of the target node. Specified for
        each group. Might be smaller than 1. Will be initialized with 0.0 for each group if None
    """
    def __init__(self, source: int, target: int, groups : List[str],
                 edge_type: AttributeAssociationEdgeType = AttributeAssociationEdgeType.UNASSIGNED,
                 positive_group: Optional[str] = None,
                 negative_group: Optional[str] = None,
                 group_size: Optional[Dict[str, int]] = None,
                 co_occurrence: Optional[Dict[str, int]] = None,
                 conditional_prevalence: Optional[Dict[str, float]] = None,
                 conditional_increase: Optional[Dict[str, float]] = None, increase_ratio: Optional[Dict[str, float]] = None):
        """Constructor method
        """
        super().__init__(source, target, BaseEdgeType.UNASSIGNED)
        self.graph_type = GraphType.AttributeAssociation
        self.edge_type = edge_type
        if len(groups) == 0:
            raise AttributeError('You have to define at least one group')
        self.groups = groups
        if positive_group is not None and negative_group is not None and positive_group == negative_group:
            raise AttributeError('Positive and negative group cannot be identical')
        if (positive_group is None) != (negative_group is None):
            raise AttributeError('Either both or none of positive and negative group have be specified')
        if positive_group is not None and positive_group not in self.groups:
            raise AttributeError('Positive group "' + positive_group + '" not in list of groups')
        if negative_group is not None and negative_group not in self.groups:
            raise AttributeError('Negative group "' + negative_group + '" not in list of groups')
        self.negative_group = negative_group
        self.positive_group = positive_group
        if group_size is not None:
            for group in self.groups:
                if group not in group_size:
                    raise AttributeError('Group size not specified for group "' + group + '"')
        self.group_size = group_size or {group : 0 for group in self.groups}
        if co_occurrence is not None:
            for group in self.groups:
                if group not in co_occurrence:
                    raise AttributeError('Co-occurrence count not specified for group "' + group + '"')
        self.co_occurrence = co_occurrence or {group : 0 for group in self.groups}
        if conditional_prevalence is not None:
            for group in self.groups:
                if group not in conditional_prevalence:
                    raise AttributeError('Conditional prevalence not specified for group "' + group + '"')
        self.conditional_prevalence = conditional_prevalence or {group : 0 for group in self.groups}
        if conditional_increase is not None:
            for group in self.groups:
                if group not in conditional_increase:
                    raise AttributeError('Conditional prevalence increase not specified for group "' + group + '"')
        self.conditional_increase = conditional_increase or {group : 0 for group in self.groups}
        if increase_ratio is not None:
            for group in self.groups:
                if group not in increase_ratio:
                    raise AttributeError('Conditional prevalence increase ratio not specified for group "' + group + '"')
        self.increase_ratio = increase_ratio or {group : 0 for group in self.groups}

    def __hash__(self):
        return hash((self.source, self.target))

    def __eq__(self, other):
        return self.source == other.source and self.target == other.target

    @staticmethod
    def get_csv_header() -> List[str]:
        return BaseEdge.get_csv_header() + ["groups[]", "co_occurrence:long[]", "conditional_prevalence:double[]",
                                            "conditional_increase:double[]", "increase_ratio:double[]"]

    @staticmethod
    def check_csv_row(row: Dict[str, str]) -> None:
        BaseEdge.check_csv_row(row)
        BaseUtils.check_csv_row(row, {
            "groups[]": str, "co_occurrence:long[]": str, "conditional_prevalence:double[]": str,
            "conditional_increase:double[]": str, "increase_ratio:double[]": str})

    def __convert_to_list(self, param_name : str):
        param_dict = getattr(self, param_name)
        return [param_dict[entry] for entry in self.groups]

    def __convert_to_str(self, param_name):
        return ';'.join((str(val) for val in self.__convert_to_list(param_name)))

    @staticmethod
    def from_csv_row(row: Dict[str, str]) -> 'AttributeAssociationEdge':
        AttributeAssociationEdge.check_csv_row(row)
        if row[':TYPE'] not in AttributeAssociationEdgeType.__members__:
            raise AttributeError('Type "' + row[':TYPE'] + '" of AttributeAssociationEdge not recognized, should be one of "'
                                 + '", "'.join(AttributeAssociationEdgeType.__members__) + '"')
        groups, group_size, pos_group, neg_group = BaseUtils.extract_group_info_from_str(row['groups[]'])
        co_occurrence = dict(zip(groups, BaseUtils.csv_row_string_to_list(row, 'co_occurrence:long[]')))
        conditional_prevalence = dict(zip(groups, BaseUtils.csv_row_string_to_list(row, 'conditional_prevalence:double[]')))
        conditional_increase = dict(zip(groups, BaseUtils.csv_row_string_to_list(row, 'conditional_increase:double[]')))
        increase_ratio = dict(zip(groups, BaseUtils.csv_row_string_to_list(row, 'increase_ratio:double[]')))


        return AttributeAssociationEdge(source=int(row[':START_ID']), target=int(row[':END_ID']), groups=groups,
                                        edge_type=AttributeAssociationEdgeType(row[':TYPE']), positive_group=pos_group,
                                        negative_group=neg_group, group_size=group_size,
                                        co_occurrence=co_occurrence, conditional_prevalence=conditional_prevalence,
                                        conditional_increase=conditional_increase, increase_ratio=increase_ratio)

    def to_csv_row(self) -> List[Union[str, int, float]]:
        return super().to_csv_row() + [
            ';'.join(BaseUtils.combine_group_info(
                self.groups, self.group_size,self.positive_group, self.negative_group)),
            self.__convert_to_str('co_occurrence'),
            self.__convert_to_str('conditional_prevalence'),
            self.__convert_to_str('conditional_increase'),
            self.__convert_to_str('increase_ratio')]

    def data_for_cypher_write_query(self) -> Tuple[str, Dict[str, Any]]:
        """Returns edge type and parameter dictionary for a Cypher MERGE statement to insert the edge into a Neo4J
        database.

        :return: Returns the data for the Cypher statement as a pair of edge type and empty parameter dictionary
        """
        edge_type, params = super().data_for_cypher_write_query()
        params['groups'] = BaseUtils.combine_group_info(
                self.groups, self.group_size,self.positive_group, self.negative_group)
        params['co_occurrence'] = self.__convert_to_list('co_occurrence')
        params['conditional_prevalence'] = self.__convert_to_list('conditional_prevalence')
        params['conditional_increase'] = self.__convert_to_list('conditional_increase')
        params['increase_ratio'] = self.__convert_to_list('increase_ratio')
        return edge_type, params