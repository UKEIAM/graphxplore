.. _aag:

graphxplore.Basis.AttributeAssociationGraph package
========================================

*Attribute association graphs* capture statistical traits of attributes (unique variable values) within groups of
primary keys as nodes, and the conditional dependencies between attributes as edges. These graphs can later be explored
visually in Neo4J without the need for coding/scripting skills. Statistical traits will be encoded by color, size and
arrow thickness.
:class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationGraph` objects are  created by
:class:`~graphxplore.GraphDataScience.AttributeAssociationGraphGenerator`.
An :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationNode` object inherits from and represents a
:class:`~graphxplore.Basis.BaseGraph.BaseNode`. It captures absolute count, missing rate and prevalence of its
attribute within each defined group. Additionally, it compares the prevalence between groups by difference and ratio.
*positive* and *negative* groups can be defined and colors will encode the association of edge node with these groups
in the visualization. :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdge` objects inherit from
:class:`~graphxplore.Basis.BaseGraph.BaseEdge` capture the conditional relationship between the attributes of their
source and target node. They contain the absolute co-occurrence, conditional
probability of the target attribute given the source attribute, and the impact of the added condition to the prevalence
of the target node's attribute.

Module contents
---------------

.. automodule:: graphxplore.Basis.AttributeAssociationGraph
   :members:
   :undoc-members:
   :show-inheritance:
