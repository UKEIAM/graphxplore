.. _graphtranslation:

graphxplore.GraphTranslation package
====================================

This subpackage contains the :class:`~graphxplore.GraphTranslation.GraphTranslator` which transforms a relational
dataset (in the form of CSV files) into a graph structure which can e.g. be loaded into a Neo4J database.
A prerequisite is a :class:`~graphxplore.MetaDataHandling.MetaData` object of the relational dataset which can be
generated with the :class:`~graphxplore.MetaDataHandling.MetaDataGenerator` class.

The result of the transformation process is a :class:`~graphxplore.Basis.BaseGraph.BaseGraph` which contains a node for
each unique table/variable/value combination in the original relational dataset. A node `x` for a primary key value has
an edge to another node `y` if the values of `x` and `y` appear in the same row of the relational dataset. As all
table/variable/value combinations are unique within the graph, two primary key values (representing their respective
CSV rows) `x1` and `x2` with the same value for one variable will both have an outgoing edge pointing to the same node
`y`.

The :class:`~graphxplore.Basis.BaseGraph.BaseGraph` can be stored in a Neo4J database (or as CSV files). The graph
structure enables efficient lookups with the Neo4J Cypher query language by value (select statements in SQL). As
foreign key relations are also stored via edges, efficient lookup across tables are also possible without tedious join
statements. The code to generate and store a :class:`~graphxplore.Basis.BaseGraph.BaseGraph` might look like

::

    >>> from graphxplore.Basis import GraphType, GraphOutputType
    >>> from graphxplore.MetaDataHandling import MetaData
    >>> from graphxplore.GraphTranslation import GraphTranslator
    >>> meta = MetaData.load_from_json(filepath='path_to_meta.json')
    >>> translator = GraphTranslator(meta)
    >>> translator.transform_to_graph(csv_data='/relational_csv_dir', output='mygraphdb',
    >>>                               output_type=GraphOutputType.Database, address='bolt://localhost:7687',
    >>>                               auth=('my_user', 'my_password'))

Module contents
---------------

.. automodule:: graphxplore.GraphTranslation
   :members:
   :undoc-members:
   :show-inheritance:
