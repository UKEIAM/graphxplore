from enum import Enum
from typing import Optional

class GraphType(str, Enum):
    """The type of graph.
    """
    Base = 'Base'
    AttributeAssociation = 'AttributeAssociation'

class Graph:
    """This is the parent class of all types of graphs. It is a data holder of nodes and edges.

    :param nodes: The list of nodes
    :param edges: The list of edges
    :param graph_type: The type of graph
    """
    def __init__(self, graph_type : GraphType, nodes : Optional[list] = None, edges : Optional[list] = None):
        self.nodes = nodes if nodes is not None else []
        self.edges = edges if edges is not None else []
        self.type = graph_type