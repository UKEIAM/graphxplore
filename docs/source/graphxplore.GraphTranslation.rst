.. _graphtranslation:

graphxplore.GraphTranslation package
====================================

This subpackage contains the :class:`~graphxplore.GraphTranslation.GraphTranslator` which transforms a relational
dataset (in the form of CSV files) into a graph structure which can e.g. be loaded into a Neo4J database.
A prerequisite is a :class:`~graphxplore.MetaDataHandling.MetaData` object of the relational dataset which can be
generated with the :class:`~graphxplore.MetaDataHandling.MetaDataGenerator` class. The result of the transformation
process is a :class:`~graphxplore.Basis.BaseGraph.BaseGraph` which contains a node for each unique variable/value
combination in the original relational dataset. A node `x` for a primary key value has an outgoing edge to another
node `y` if the values of `x` and `y` appear in the same row of the relational dataset. As all variable/value
combinations are unique within the graph, two primary key values (representing their respective CSV rows) `x1` and `x2`
with the same value for one variable will both have an outgoing edge to the same node `y`.
As a result lookups by value (select statements in SQL) can be done very efficiently. Foreign key relations are also
stored this way, enabling efficient lookup across tables without tedious join statements. The
:class:`~graphxplore.GraphTranslation.GraphTranslator` writes the generated graph to CSV files which can be loaded
into a Neo4J database. The code might look like

::

    >>> from graphxplore.Basis import GraphCSVReader, GraphDatabaseWriter, GraphType
    >>> from graphxplore.MetaDataHandling import MetaData
    >>> from graphxplore.GraphTranslation import GraphTranslator
    >>> meta = MetaData.load_from_json(filepath='path_to_meta.json')
    >>> translator = GraphTranslator(meta)
    >>> translator.generate_graph_tables(data_dir='relational_csv_dir', output='graph_dir')
    >>> reader = GraphCSVReader(graph_dir='graph_dir', graph_type=GraphType.Base)
    >>> reloaded_graph = reader.read_graph()
    >>> GraphDatabaseWriter.write_graph(db_name='mygraph', graph=reloaded_graph, overwrite=False, host='localhost',
    >>>                                 bolt_port=7687, auth=('my_user', 'my_password'))

Module contents
---------------

.. automodule:: graphxplore.GraphTranslation
   :members:
   :undoc-members:
   :show-inheritance:
