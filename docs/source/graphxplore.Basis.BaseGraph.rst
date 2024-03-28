.. _basegraph:

graphxplore.Basis.BaseGraph package
===================================

A *base graph* in graphxplore represents a relational dataset as a graph structure which can be stored in a Neo4J
database. This enables efficient data retrieval and forms the basis of all data exploration tasks.
The :class:`~graphxplore.Basis.BaseGraph.BaseGraph` object is the graph structure that is created by
:class:`~graphxplore.GraphTranslation.GraphTranslator`. A :class:`~graphxplore.Basis.BaseGraph.BaseNode` represents a
unique value of a variable. A node `x` for a primary key value has an outgoing
:class:`~graphxplore.Basis.BaseGraph.BaseEdge` to another node `y` if the values of `x` and `y` appear in the same row
of the relational data table. As all variable/value combinations are unique within the graph, two primary key values
(representing their respective CSV rows) `x1` and `x2` with the same value for one variable will both have an outgoing
edge to the same node `y`. As a result, lookups by value (select statements in SQL) can be done very efficiently.
Foreign key relations are also stored this way, enabling efficient lookup across tables without tedious join statements.

Module contents
---------------

.. automodule:: graphxplore.Basis.BaseGraph
   :members:
   :undoc-members:
   :show-inheritance:
