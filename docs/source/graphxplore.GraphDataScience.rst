.. _graphdatascience:

graphxplore.GraphDataScience package
====================================

This subpackage contains functionality for exploratory data analysis using knowledge graphs. The starting point is a
Neo4j database containing the data of a :class:`~graphxplore.Basis.BaseGraph.BaseGraph`. With the
:class:`~graphxplore.GraphDataScience.KnowledgeGraphGenerator` class the user can generate a
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeGraph`. A breadth-first-search (BFS) strategy is applied starting
from a user-defined group of primary keys and capturing connected nodes representing variable/value combinations which
occur for some primary key in the group. The :class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeNode` of the resulting
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeGraph` capture `absolute count`, `relative total share` (absolute
count divided by group size) and `relative attribute share` (absolute count divided by number of primary keys without
missing value for the variable) of a variable/value combination within the group of primary keys. The nodes are labeled
as `infrequent` (relative attribute share < 10%), `frequent` ( 10% <= relative attribute share < 50%) or
`highly frequent` (relative attribute share >= 50%).
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeEdge` from node `x` to `y` captures the conditional relationship
between nodes (i.e between variable/value combinations). They contain the absolute co-occurrence, conditional
probability of `y` given `x`, and the (not absolute) difference and quotient between that conditional relationship and
the relative attribute share of `y`. Edges are labeled as `low conditional difference` (if absolute difference < 10% and
quotient < 1.5 and > 0.66), `medium conditional difference` (if 10% <= absolute difference < 20% or quotient in [1.5;2]
or in [0.5;0.66]), or else as `high conditional difference` (absolute difference >= 20% or quotient > 2 or < 0.5).


The group of primary keys can be defined by a Cypher (Neo4j query language) statement. The variable/value combinations
can be pre-filtered by origin table, variable name and value constraints with
:class:`~graphxplore.GraphDataScience.KnowledgeGraphAttributeFilter` objects. The nodes and edges of a generated
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeGraph` can be post-filtered by thresholds for their statistical
traits with :class:`~graphxplore.GraphDataScience.GraphFilter`. Code might look like

::

    >>> from graphxplore.Basis import GraphCSVWriter
    >>> from graphxplore.GraphDataScience import KnowledgeGraphGenerator, KnowledgeGraphAttributeFilter, AttributeFilter, StringFilterType, NumericFilterType, GraphFilter, PropFilter
    >>> no_nanas = AttributeFilter('nana', StringFilterType.Contains, include=False)
    >>> negative_or_large = [AttributeFilter(0, NumericFilterType.Smaller, include=True),
    >>>                      AttributeFilter(100, NumericFilterType.LargerOrEqual, include=True)]
    # captured variable/value combinations cannot originate from 'forbidden_table', cannot contain 'nana' in their
    # variable name, and their value must be a string, or be negative or at least 100
    >>> pre_filter = KnowledgeGraphAttributeFilter(blacklist_tables=['forbidden_table'], name_filters=[no_nanas],
    >>>                                            value_filters=negative_or_large)
    >>> min_count_filter = PropFilter(prop_to_filter='abs_count', min_val=10)
    >>> post_filter = GraphFilter(node_filter=min_count_filter)
    # select all primary keys 'pk' from 'table'
    >>> KnowledgeGraphGenerator(db_name='mygraphdb', primary_table='table', primary_name='pk')
    # select primary keys 'pk' from 'table' if they are connected to (are in same relational row with) the value
    # 'apple' of variable 'food'
    >>> KnowledgeGraphGenerator(db_name='mygraphdb', primary_table='table', primary_name='pk',
    >>>                         primary_match='match(n)--(:Attribute {name:"food",value:"apple"})')
    # add pre and post filter
    >>> generator = KnowledgeGraphGenerator(db_name='mygraphdb', primary_table='table', primary_name='pk',
    >>>                                     primary_match='match(n)--(:Attribute {name:"food",value:"apple"})',
    >>>                                     attribute_filter=pre_filter, graph_filter=post_filter, host='localhost',
    >>>                                     bolt_port=7687, auth=('my_user', 'my_password'))
    >>> knowledge_graph = generator.generate_knowledge_graph()
    # write result to CSV files
    >>> GraphCSVWriter.write_graph(graph_dir='out_dir', graph=knowledge_graph))

Within an exploratory data analysis it can be interesting to compare statistics between groups (e.g. between a disease
and a control cohort) to find variable/value combinations that might be associated with the groups (e.g. with a
disease). First, you need to generate multiple :class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeGraph` objects
(stored as CSV files) originating from the same :class:`~graphxplore.Basis.BaseGraph.BaseGraph` as described above. The
:class:`~graphxplore.GraphDataScience.KnowledgeGraphSummarizer` class then generates a
:class:`~graphxplore.Basis.KnowledgeSummaryGraph.KnowledgeSummaryGraph` which contains all data of the individual
:class:`~graphxplore.Basis.KnowledgeGraph.KnowledgeGraph` objects. Additionally, the `relative total share`  and
`relative attribute share` scores are compared between groups (by absolute difference and quotient). The user might
define a positive (e.g. disease) group and a negative (e.g. control) group. Based on the
comparison of `relative attribute share` scores of the positive and negative group, nodes are labeled as
`highly inverse` (score 2x larger (or >= 20% absolute difference) for negative group), `inverse` (score 1.5x larger
(or >= 10% absolute difference) for negative group), `unrelated` (quotient < 1.5 and absolute difference < 10%),
`related` (score 1.5x larger (or >= 10% absolute difference) for positive group), or `highly related` (score 2x larger
(or >= 20% absolute difference) for positive group). Again, the nodes and edges of the generated
:class:`~graphxplore.Basis.KnowledgeSummaryGraph.KnowledgeSummaryGraph` can be post-filtered using a
:class:`~graphxplore.GraphDataScience.GraphFilter`. Code might look like

::

    >>> from graphxplore.Basis import GraphDatabaseWriter
    >>> from graphxplore.GraphDataScience import KnowledgeGraphSummarizer, GraphFilter, PropFilter, OrFilterCascade, GroupFilterMode
    >>> graphs_to_summarize = {'DiseaseGroup' : 'path/to/disease/group', 'ControlGroup' : 'path/to/control/group'}
    # node filter: high absolute difference between relative attribute shares of groups
    >>> high_diff = PropFilter(prop_to_filter='diff_rel_share_attr', min_val=0.4)
    # node_filter: low absolute count in both individual knowledge graphs
    >>> low_count = PropFilter(prop_to_filter='abs_count', max_val=10, applies_to=GroupFilterMode.All)
    >>> high_diff_or_low_count = OrFilterCascade(filters=[high_diff, low_count])
    # edge filter:  quotient of conditional probability and target relative attribute share between 1.2 and 1.4 for at least one group
    >>> medium_quot_target = PropFilter(prop_to_filter='quot_target', min_val=1.2, max_val=1.4, applies_to=GroupFilterMode.Any)
    >>> post_filter = GraphFilter(node_filter=high_diff_or_low_count, edge_filter=medium_quot_target)
    >>> summarizer = KnowledgeGraphSummarizer(group_graphs=graphs_to_summarize, graph_filter=post_filter,
    >>>                                       positive_group='DiseaseGroup', negative_group='ControlGroup')
    >>> summary_graph = summarizer.combine_knowledge_graphs()
    # store graph in database
    >>> GraphDatabaseWriter.write_graph(db_name='mysummarygraph', graph=summary_graph, overwrite=True, host='localhost',
    >>>                                 bolt_port=7687, auth=('my_user', 'my_password'))


Module contents
---------------

.. automodule:: graphxplore.GraphDataScience
   :members:
   :undoc-members:
   :show-inheritance:
