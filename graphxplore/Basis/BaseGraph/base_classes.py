import hashlib
from dataclasses import dataclass
from typing import Union, Optional, List, Tuple, Dict, Any
from enum import Enum
from ..graph_classes import Graph, GraphType
from ..utils import BaseUtils

class BaseGraph(Graph):
    """This is the graph holding :class:`BaseNode` and :class:`BaseEdge` objects. It forms the basis of all further
    data science procedures.

    :param nodes: The list of nodes
    :param edges: The list of edges
    """
    def __init__(self, nodes : Optional[List['BaseNode']] = None, edges : Optional[List['BaseEdge']] = None):
        super().__init__(GraphType.Base, nodes, edges)

class BaseNodeType(str, Enum):
    """The type of :class:`BaseNode`
    """
    Key = 'Key'
    Attribute = 'Attribute'
    AttributeBin = 'AttributeBin'

class BaseLabels:
    """The labels assigned to a :class:`BaseNode`.

    :param membership_labels: One or more labels describing the membership of the node into categories. The origin table
        should always be one label
    :param node_type: The type of node
    """
    def __init__(self, membership_labels : Tuple[str, ...], node_type : BaseNodeType):
        """Constructor method
        """
        self.membership_labels = membership_labels
        self.node_type = node_type

    @staticmethod
    def from_label_string(label_string : str) -> 'BaseLabels':
        """Generate a :class:`BaseLabels` object from a label string. The single values should be seperated by
        semicolons and the :class:`BaseNodeType` label should appear last. Raises an exception if parsing failed.

        :param label_string: The input string from which the object is parsed
        :return: Returns the parsed object
        """
        labels = label_string.split(';')
        if len(labels) < 2:
            raise AttributeError('Label string "' + label_string
                                 + '" is invalid, it should contain at least one label for the table or other '
                                   'affiliation and the node type as the last element')
        node_type_string = labels[-1]
        if node_type_string not in BaseNodeType.__members__:
            raise AttributeError('The last entry of the label string "' + label_string
                                 + '" must describe the node type with one of: "'
                                 + '", "'.join(BaseNodeType.__members__) + '"')

        return BaseLabels(membership_labels=tuple(labels[:-1]), node_type=BaseNodeType(node_type_string))

    def to_label_string(self) -> str:
        """Converts the object to a string. The individual labels are concatenated by semicolons, the
        :class:`BaseNodeType` appears last.

        :return: Returns the converted string
        """
        return ';'.join(self.membership_labels) + ';' + self.node_type

@dataclass
class BinBoundInfo:
    """The lower and upper bound for a 'normal' value. Values above `ref_upper` are considered 'high', below `ref_lower`
    as 'low'.

    :param ref_lower: The lower bound
    :param ref_upper: The upper bound
    """
    ref_lower : float
    ref_upper : float

class NodeDataType(str, Enum):
    """The datatype of the `value` parameter of a :class:`BaseNode`.
    """
    String = 'String'
    Integer = 'Integer'
    Decimal = 'Decimal'
    Bin = 'Bin'

class BaseNode:
    """The base node class from which most other node classes inherit. It contains the name of a column and the cell
    value, and additionally a description, labels and binning info (if the node is of type 'AttributeBin').

    :param node_id: The ID of the node, used for various lookups.
    :param labels: The labels of the node's origin table and categories
    :param name: The column name
    :param val: The cell value
    :param desc: The description of the data column
    :param bin_info: The lower and upper bound used for binning
    """
    def __init__(self, node_id : int, labels : BaseLabels, name : str, val : Union[str, int, float],
                 desc : Optional[str] = None, bin_info : Optional[BinBoundInfo] = None):
        """Constructor method
        """
        self.node_id = node_id
        self.labels = labels
        self.name = name
        self.val = val
        # self.desc = desc if desc is not None else ''
        self.desc = desc
        self.bin_info = bin_info
        if self.bin_info is not None:
            self.data_type = NodeDataType.Bin
        elif type(self.val) == str:
            self.data_type = NodeDataType.String
        elif type(self.val) == int:
            self.data_type = NodeDataType.Integer
        else:
            self.data_type = NodeDataType.Decimal
        self.graph_type = GraphType.Base

    def __hash__(self):
        if isinstance(self.val, str) and (len(self.val) > 300 or "\n" in self.val):
            short_hash = int(hashlib.md5(self.val.encode()).hexdigest(), 16)
            return hash((self.labels.node_type, self.labels.membership_labels, self.name, short_hash))
        return hash((self.labels.node_type, self.labels.membership_labels, self.name, self.val))

    def __eq__(self, other):
        return self.labels.membership_labels == other.labels.membership_labels\
               and self.labels.node_type == other.labels.node_type\
               and self.name == other.name\
               and self.val == other.val

    @staticmethod
    def check_csv_row(row: Dict[str, str]) -> None:
        """Checks if all required fields are present in the CSV row and have the correct data type.

        :param row: The CSV row to check
        """
        BaseUtils.check_csv_row(row, {':ID' : int, ':LABEL' : str, 'name' : str, 'description' : str})

    @staticmethod
    def get_csv_header(data_type : NodeDataType) -> List[str]:
        """Generates the header for a CSV storing the nodes

        :param data_type: The data type of the nodes `value`
        :return: Returns the generated header
        """
        value_attr = 'value'
        if data_type == NodeDataType.String or data_type == NodeDataType.Bin:
            pass
        elif data_type == NodeDataType.Integer:
            value_attr += ':long'
        elif data_type == NodeDataType.Decimal:
            value_attr += ':double'
        else:
            raise AttributeError('Node data type invalid')
        header = [":ID", ":LABEL", "name", value_attr, "description"]
        if data_type == NodeDataType.Bin:
            header += ["refRange:double[]"]
        return header

    @staticmethod
    def _get_value_and_bin_info_from_csv_row(row : Dict[str, str]) -> Tuple[Union[str, int, float],
                                                                            Optional[BinBoundInfo]]:
        """Parses the value and optionally a :class:`BinBoundInfo` object (if the entries exist) from a CSV row.

        :param row: The CSV row as dictionary
        :return: Returns a pair of parsed objects
        """
        # infer data type
        value_key = None
        for key in row.keys():
            if 'value' in key:
                value_key = key
                break
        if value_key is None:
            raise AttributeError('CSV row must contain a key "value", "value:long", or "value:double"')

        if ':long' in value_key:
            try:
                casted_value = int(row[value_key])
            except ValueError:
                raise AttributeError('"' + row[value_key] + '" is not of type integer')
        elif ':double' in value_key:
            try:
                casted_value = float(row[value_key])
            except ValueError:
                raise AttributeError(row[value_key] + ' is not of type float')
        else:
            casted_value = row[value_key]

        bin_info = None
        if 'refRange:double[]' in row:
            ref_range = [float(entry) for entry in row['refRange:double[]'].split(';')]
            bin_info = BinBoundInfo(ref_range[0], ref_range[1])
        return casted_value, bin_info

    @staticmethod
    def from_csv_row(row : Dict[str, str]) -> 'BaseNode':
        """Parses a node from a CSV row.

        :param row: The CSV row as a dictionary
        :return: Return the parsed objects
        """
        casted_value, bin_info = BaseNode._get_value_and_bin_info_from_csv_row(row)
        BaseNode.check_csv_row(row)
        return BaseNode(node_id=int(row[':ID']), labels=BaseLabels.from_label_string(row[':LABEL']), name=row['name'],
                        val=casted_value, desc=row['description'], bin_info=bin_info)

    def to_csv_row(self) -> List[Union[str, float, int]]:
        """Converts the object to a csv row as list.

        :return: Returns the list
        """
        row = [self.node_id, self.labels.to_label_string(), self.name, self.val, self.desc]
        if self.bin_info is not None:
            row += [str(self.bin_info.ref_lower) + ';' + str(self.bin_info.ref_upper)]
        return row

    def data_for_cypher_write_query(self) -> Tuple[List[str], Dict[str, Any]]:
        """Returns labels and parameter dictionary for a Cypher MERGE statement to insert the node into a Neo4J
        database.

        :return: Returns the data for the Cypher statement as a pair of label list and parameter dictionary
        """
        labels = self.labels.to_label_string().split(';')
        params = {'name' : self.name, 'value' : self.val, 'description' : self.desc or ''}
        if self.bin_info is not None:
            params['refRange'] = [self.bin_info.ref_lower, self.bin_info.ref_upper]
        return labels, params

class BaseEdgeType(str, Enum):
    """The type of :class:`BaseEdge`.

    - UNASSIGNED: invalid, has to be reset later
    - HAS_ATTR_VAL: points from a primary key node to an attribute node contained in its relational table row
    - CONNECTED_TO: points from a foreign key node to the primary key node in the same relational table row
    - ASSIGNED_BIN: points from an attribute node of a metric variable to its assigned attribute bin node
    """
    UNASSIGNED = 'UNASSIGNED'
    HAS_ATTR_VAL = 'HAS_ATTR_VAL'
    CONNECTED_TO = 'CONNECTED_TO'
    ASSIGNED_BIN = 'ASSIGNED_BIN'

@dataclass
class BaseEdge:
    """This class is the parent of almost all other types of edges. It resembles a directed edge point from a source
    node to a target node.

    :param source: The ID of the source :class:`BaseNode`
    :param target: The ID of the source :class:`BaseNode`
    :param edge_type: The type of base edge
    """
    def __init__(self, source : int, target : int, edge_type : BaseEdgeType):
        """Constructor method
        """
        self.source = source
        self.target = target
        self.edge_type = edge_type
        self.graph_type = GraphType.Base

    def __hash__(self):
        return hash((self.source, self.target, self.edge_type))

    def __eq__(self, other : 'BaseEdge'):
        return self.source == other.source\
               and self.target == other.target\
               and self.edge_type == other.edge_type

    @staticmethod
    def get_csv_header() -> List[str]:
        """Generates the header for a CSV storing the edges.

        :return: Returns the generated header
        """
        return [":START_ID", ":END_ID", ":TYPE"]

    @staticmethod
    def check_csv_row(row: Dict[str, str]) -> None:
        """Checks if all required fields are present in the CSV row and have the correct data type.

        :param row: The CSV row to check
        """
        BaseUtils.check_csv_row(row, {':START_ID': int, ':END_ID': str, ':TYPE': str})

    @staticmethod
    def from_csv_row(row: Dict[str, str]) -> 'BaseEdge':
        """Parses an edge from a CSV row.

        :param row: The CSV row as a dictionary
        :return: Return the parsed objects
        """
        BaseEdge.check_csv_row(row)
        if row[':TYPE'] not in BaseEdgeType.__members__:
            raise AttributeError('Type "' + row[':TYPE'] + '" of BaseEdge not recognized, should be one of "'
                                 + '", "'.join(BaseEdgeType.__members__) + '"')
        return BaseEdge(int(row[':START_ID']), int(row[':END_ID']), BaseEdgeType(row[':TYPE']))

    def to_csv_row(self) -> List[Union[str, int, float]]:
        """Converts the object to a csv row as list.

        :return: Returns the list
        """
        return [self.source, self.target, self.edge_type.value]

    def data_for_cypher_write_query(self) -> Tuple[str, Dict[str, Any]]:
        """Returns edge type and empty parameter dictionary for a Cypher MERGE statement to insert the edge into a Neo4J
        database.

        :return: Returns the data for the Cypher statement as a pair of edge type and empty parameter dictionary
        """
        return self.edge_type.value, {}




