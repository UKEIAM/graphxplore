.. _knowledgesummarygraph:

graphxplore.Basis.KnowledgeSummaryGraph package
===============================================

The :class:`~graphxplore.Basis.KnowledgeSummaryGraph.KnowledgeSummaryGraph` object is the graph structure that is
created by :class:`~graphxplore.GraphDataScience.KnowledgeGraphSummarizer`. Each
:class:`~graphxplore.Basis.KnowledgeSummaryGraph.KnowledgeSummaryNode` of the graph combines the data from multiple
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeNode` objects referencing the same
:class:`~graphxplore.Basis.BaseGraph.BaseNode` but describing statistical data for different primary key groups. This
way groups (e.g. disease and control groups) in the dataset can be compared and variable/value combinations with
differing statistical traits among the groups can be identified. These could be used e.g. in a follow-up correlation
analysis. :class:`~graphxplore.Basis.KnowledgeSummaryGraph.KnowledgeSummaryEdge` also combine data from
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeEdge` for comparison by the user. This way the conditional
relationships between variable/value combinations can be investigated in the context of different primary key groups.

Module contents
---------------

.. automodule:: graphxplore.Basis.KnowledgeSummaryGraph
   :members:
   :undoc-members:
   :show-inheritance:
