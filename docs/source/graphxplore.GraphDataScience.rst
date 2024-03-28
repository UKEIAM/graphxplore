.. _graphdatascience:

graphxplore.GraphDataScience package
====================================

This subpackage contains functionality for exploratory data analysis using *attribute association graphs*. The starting
point is a Neo4j database containing the data of a :class:`~graphxplore.Basis.BaseGraph.BaseGraph`. With the
:class:`~graphxplore.GraphDataScience.AttributeAssociationGraphGenerator` class, the user can generate an
:class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationGraph`. The user must provide one or multiple
groups of primary keys using the :class:`~graphxplore.GraphDataScience.GroupSelector` or manually writing Neo4J Cypher
queries. Several statistical traits of
each attribute (table/variable/value combination) are measured for each group as well as conditional dependencies
between attributes. This is done with a breadth-first-search (BFS) strategy starting from the primary keys contained
in the group and traversing to all connected attributes in the table itself and potentially foreign tables (and
foreign tables of foreign tables...). Attributes can be pre-filtered by table, name and value using
:class:`~graphxplore.GraphDataScience.AttributeAssociationGraphPreFilter` objects, or the generated
:class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationGraph` can be post-filtered by statistical
traits using :class:`~graphxplore.GraphDataScience.AttributeAssociationGraphPostFilter` objects.

The statistical traits of single attributes (absolute count, percentage in groups, missing data ratio, percentage
difference and ratio) are stored in
:class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationNode` objects where all parameters are
explained in detail. All nodes are assigned a :class:`~graphxplore.Basis.AttributeAssociationGraph.FrequencyLabel`
based on their prevalence (percentage of occurrence in group) and the ``frequency_thresholds`` parameter of
:class:`~graphxplore.GraphDataScience.AttributeAssociationGraphGenerator`. This label will impact the size of the
circle depicting the node in the visualization. This way, the attention of the user is drawn to more frequently
appearing attributes. Additionally, nodes are assigned a
:class:`~graphxplore.Basis.AttributeAssociationGraph.DistinctionLabel` (if ``positive_group`` and ``negative_group`` of
:class:`~graphxplore.GraphDataScience.AttributeAssociationGraphGenerator` are set) based on their prevalence
difference and ratio and the ``prevalence_diff_thresholds`` and ``prevalence_ratio_thresholds`` parameters of
:class:`~graphxplore.GraphDataScience.AttributeAssociationGraphGenerator` (at least one threshold must be passed).
This label impacts the color of the nodes with red or orange (higher prevalence in ``positive_group``), beige (roughly
same prevalence in ``positive_group`` and ``negative_group``), or turquoise or blue (higher prevalence in
``negative_group``). This way, attention is drawn to attributes which might be associated with the selected groups.

The conditional dependencies (absolute co-occurrence, conditional prevalence of the target attribute given the source
attribute, comparison of conditional and unconditional target prevalence via difference and ratio) are stored in
:class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdge` objects and explained there in detail.
All edges are assigned an :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdgeType` based on
the difference and ratio of the conditional and unconditional prevalence, and the ``cond_increase_thresholds``
and ``increase_ratio_thresholds`` parameters of
:class:`~graphxplore.GraphDataScience.AttributeAssociationGraphGenerator` (at least one threshold must be passed).

Code might look like

::

    >>> from graphxplore.Basis import GraphDatabaseWriter
    >>> from graphxplore.MetaDataHandling import MetaData
    >>> from graphxplore.GraphDataScience import (AttributeAssociationGraphGenerator, CompositionGraphPostFilter,
    >>>                                           AttributeFilter, StringFilterType, NumericFilterType,
    >>>                                           AttributeAssociationGraphPreFilter, GroupSelector)
    >>> from graphxplore.DataMapping.Conditionals import StringOperator, StringOperatorType, NegatedOperator
    >>>
    >>> my_meta = MetaData.load_from_json(filepath='/meta_path.json')
    # define a group of primary keys which have the attribute 'apple' of variable 'food' and a control group not
    # having this attribute
    >>> apple_condition = StringOperator(table='table',variable='food',value='apple', compare=StringOperatorType.Equals)
    >>> apple_group = GroupSelector(group_table='table',meta=my_meta,
    >>>                             group_filter=apple_condition)
    >>> control_group = GroupSelector(group_table='table',meta=my_meta,
    >>>                               group_filter=NegatedOperator(pos_operator=apple_condition)
    # captured variable/value combinations cannot originate from 'forbidden_table', cannot contain 'nana' in their
    # variable name, and their value must be a string, or be negative or at least 100
    >>> no_nanas = AttributeFilter('nana', StringFilterType.Contains, include=False)
    >>> negative_or_large = [AttributeFilter(0, NumericFilterType.Smaller, include=True),
    >>>                      AttributeFilter(100, NumericFilterType.LargerOrEqual, include=True)]
    >>> pre_filter = AttributeAssociationGraphPreFilter(blacklist_tables=['forbidden_table'], name_filters=[no_nanas],
    >>>                                                 value_filters=negative_or_large)
    # use a composition filter for post-filtering which removes 50% of nodes and enforces a ratio of 10% high
    # prevalence, 70% high prevalence difference, and 20% high prevalence ratio
    >>> node_ratio = (0.1,0.7,0.2)
    >>> post_filter = CompositionGraphPostFilter(node_comp_ratio=node_ratio)
    >>> generator = AttributeAssociationGraphGenerator(
    >>>     db_name='mygraphdb', group_selection={'Apple' : apple_group, 'NoApple' : control_group},
    >>>     positive_group='Apple', negative_group='NoApple', pre_filter=pre_filter, post_filter=post_filter,
    >>>     address='bolt://localhost:7687', auth=('my_user', 'my_password'))
    >>> aag = generator.generate_graph()
    # write graph to Neo4J database
    >>> GraphDatabaseWriter.write_graph(db_name='apple_aag', graph=aag, address='bolt://localhost:7687',
    >>>                                 auth=('my_user', 'my_password'))

Module contents
---------------

.. automodule:: graphxplore.GraphDataScience
   :members:
   :undoc-members:
   :show-inheritance:
