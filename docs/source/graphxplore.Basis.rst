.. _basis:

graphxplore.Basis package
=========================

This subpackage contains all graph data structures in the subpackages :ref:`basegraph` and :ref:`aag`. Additionally,
several utility functionalities like file format detection and statistical score calculation can be done with
the :class:`~graphxplore.Basis.BaseUtils` class. :class:`~graphxplore.Basis.GraphCSVReader`,
:class:`~graphxplore.Basis.GraphCSVWriter` and :class:`~graphxplore.Basis.GraphDatabaseWriter` classes can be used for
IO handling of graph structures. Building and writing a :class:`~graphxplore.Basis.BaseGraph.BaseGraph`
(:class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationGraph` follows the same rationale) to a Neo4J
database might look like

::

    >>> from graphxplore.Basis.BaseGraph import BaseGraph, BaseNode, BaseEdge, BaseLabels, BaseNodeType, BaseEdgeType
    >>> from graphxplore.Basis import GraphDatabaseWriter
    >>> base_graph = BaseGraph()
    >>> pk_node = BaseNode(node_id=0, labels=BaseLabels(membership_labels=('FirstTable',),
    >>>                    node_type=BaseNodeType.Key), name='first_primary_key', val=42)
    >>> base_graph.nodes.append(pk_node)
    >>> first_attr_node = BaseNode(node_id=1, labels=BaseLabels(membership_labels=('FirstTable',),
    >>>                            node_type=BaseNodeType.Attribute), name='attribute', val='value')
    >>> base_graph.nodes.append(first_attr_node)
    >>> fk_node = BaseNode(node_id=2, labels=BaseLabels(membership_labels=('SecondTable',),
    >>>                    node_type=BaseNodeType.Key), name='second_primary_key', val=1337)
    >>> base_graph.nodes.append(fk_node)
    >>> second_attr_node = BaseNode(node_id=3, labels=BaseLabels(membership_labels=('SecondTable',),
    >>>                             node_type=BaseNodeType.Attribute), name='measurement', val=0.25)
    >>> base_graph.nodes.append(second_attr_node)
    # row in table 'FirstTable' of primary key value 42 has value 'value' for variable 'attribute'
    >>> base_graph.edges.append(BaseEdge(source=0, target=1, edge_type=BaseEdgeType.HAS_ATTR_VAL))
    # row in table 'SecondTable' of primary key value 1337 has value 0.25 for variable 'measurement'
    >>> base_graph.edges.append(BaseEdge(source=2, target=3, edge_type=BaseEdgeType.HAS_ATTR_VAL))
    # row in table 'SecondTable' of primary key value 1337 is referenced as foreign key
    # in row in table 'FirstTable' of primary key value 42
    >>> base_graph.edges.append(BaseEdge(source=2, target=0, edge_type=BaseEdgeType.CONNECTED_TO))
    # write graph to Neo4J database 'mygraph'
    >>> GraphDatabaseWriter.write_graph(db_name='mygraph', graph=base_graph, overwrite=False,
                                        address='bolt://localhost:7687', auth=('my_user', 'my_password'))

Submodules
-----------

.. toctree::
   :maxdepth: 1

   graphxplore.Basis.BaseGraph
   graphxplore.Basis.AttributeAssociationGraph

Module contents
---------------

.. automodule:: graphxplore.Basis
   :members:
   :undoc-members:
   :show-inheritance:
