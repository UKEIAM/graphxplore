.. _knowledgegraph:

graphxplore.Basis.KnowledgeGraph package
========================================

The :class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeGraph` object is the graph structure that is created by
:class:`~graphxplore.GraphDataScience.KnowledgeGraphGenerator`. Each
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeNode` of the graph inherits from and represents a
:class:`~graphxplore.Basis.BaseGraph.BaseNode`. It captures `absolute count`, `relative total share` (absolute
count divided by group size) and `relative attribute share` (absolute count divided by number of primary keys without
missing value for the variable) of a variable/value combination within the group of primary keys.
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeEdge` from node `x` to `y` capture the conditional relationship
between nodes (i.e between variable/value combinations). They contain the absolute co-occurrence, conditional
probability of `y` given `x`, and the difference and quotient between that conditional relationship and the relative
attribute share of `y`.

Module contents
---------------

.. automodule:: graphxplore.Basis.KnowledgeGraph
   :members:
   :undoc-members:
   :show-inheritance:
