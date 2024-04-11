import collections
import copy
import csv
import json
import os
import math
import contextlib
import re
import base64
try:
    import pyodide.http
    import pyodide.webloop
    import pyodide.ffi
    from js import XMLHttpRequest, Blob
    # from streamlit.web.server.server import Server
    # import base64
    USE_PYODIDE = True
except (ModuleNotFoundError, ImportError):
    from neo4j import GraphDatabase, exceptions
    USE_PYODIDE = False
from typing import Union, Tuple, List, Iterable, Dict, Any, Optional
from enum import Enum
from .utils import BaseUtils
from .graph_classes import Graph, GraphType
from .BaseGraph.base_classes import BaseNode, BaseEdge, NodeDataType, BaseGraph, BaseNodeType
from .AttributeAssociationGraph.attribute_association_graph_classes import (AttributeAssociationGraph, FrequencyLabel,
                                                                            AttributeAssociationNode,
                                                                            AttributeAssociationEdge)

class GraphOutputType(str, Enum):
    """The type of output format for a graph
    """
    CSV = 'CSV'
    Database = 'Database'

class GraphCSVIODevice:
    """This is a parent class for reading and writing CSV files containing generated :class:`Graph` objects.

    :param graph_dir: The directory to which the graph is written or from which it is read
    :param graph_type: The type of :class:`Graph`.
    """
    def __init__(self, graph_dir : str, graph_type : GraphType):
        """Constructor method
        """
        self.graph_dir = graph_dir
        if not os.path.isdir(self.graph_dir):
            raise NotADirectoryError('Path "' + self.graph_dir + '" is not a valid directory')
        self.graph_type = graph_type
        self.file_paths = {'String' : 'Node_Table_String.csv', 'Integer' : 'Node_Table_Integer.csv',
                           'Decimal' : 'Node_Table_Decimal.csv', 'Bin' : 'Node_Table_Bin.csv',
                           'EdgeMain' : 'Relationship_Table_Main.csv'}

class GraphCSVReader(GraphCSVIODevice):
    """This class reads :class:`Graph` objects from CSV files.

    :param graph_dir: The directory containing the CSV files that will be read
    :param graph_type: The type of :class:`Graph`.
    """
    def __init__(self, graph_dir : str, graph_type : GraphType):
        """Constructor method
        """
        super().__init__(graph_dir, graph_type)
        if self.graph_type == GraphType.Base:
            self.result = BaseGraph()
        elif self.graph_type == GraphType.AttributeAssociation:
            self.result = AttributeAssociationGraph()
        else:
            raise NotImplemented('Type of graph not implemented')

    def read_graph(self) -> Graph:
        """Reads a graph from the specified source directory.

        :return: Returns the read graph
        """
        with contextlib.ExitStack() as stack:
            for file_type, path in self.file_paths.items():
                full_path = os.path.join(self.graph_dir, path)
                if not os.path.isfile(full_path):
                    raise FileNotFoundError('Path ' + full_path + ' to file not found')
                file = stack.enter_context(open(full_path))
                reader = csv.DictReader(file)
                self.__process_reader(reader, 'Edge' not in file_type)
            return self.result

    def __process_reader(self, reader : csv.DictReader, node_file : bool) -> None:
        """Reads the entries of a single CSV file containing node or edge data.

        :param reader: The CSV reader
        :param node_file: If `True` node are generated based on the specified graph type, edges otherwise
        """
        for row in reader:
            try:
                if self.graph_type == GraphType.Base:
                    if node_file:
                        self.result.nodes.append(BaseNode.from_csv_row(row))
                    else:
                        self.result.edges.append(BaseEdge.from_csv_row(row))
                elif self.graph_type == GraphType.AttributeAssociation:
                    if node_file:
                        self.result.nodes.append(AttributeAssociationNode.from_csv_row(row))
                    else:
                        self.result.edges.append(AttributeAssociationEdge.from_csv_row(row))
                else:
                    raise NotImplemented('Type of graph not implemented')
            except KeyError as e:
                raise AttributeError('Specified graph type does not match CSV file, error was: ' + str(e))


class GraphCSVWriter(GraphCSVIODevice):
    """This class writes nodes and edges, and whole :class:`Graph` object to a target directory in the form of CSV
    files.

    :param graph_dir: The directory the CSV files are written to
    :param graph_type: The type of :class:`Graph`.
    """
    def __init__(self, graph_dir : str, graph_type : GraphType):
        """Constructor method
        """
        super().__init__(graph_dir, graph_type)
        self.files = []
        self.writers = {'String' : None, 'Integer' : None, 'Decimal' : None, 'Bin' : None, 'EdgeMain' : None}

    def __enter__(self):
        for file_type, path in self.file_paths.items():
            file = open(os.path.join(self.graph_dir, path), 'w').__enter__()
            self.files.append(file)
            writer = csv.writer(file)
            if self.graph_type == GraphType.Base:
                if 'Edge' not in file_type:
                    writer.writerow(BaseNode.get_csv_header(NodeDataType[file_type]))
                else:
                    writer.writerow(BaseEdge.get_csv_header())
            elif self.graph_type == GraphType.AttributeAssociation:
                if 'Edge' not in file_type:
                    writer.writerow(AttributeAssociationNode.get_csv_header(NodeDataType(file_type)))
                else:
                    writer.writerow(AttributeAssociationEdge.get_csv_header())
            else:
                raise AttributeError('Graph type CSV writing not implemented')
            self.writers[file_type] = writer
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for file in self.files:
            file.__exit__(exc_type, exc_val, exc_tb)

    def write_node(self, node : Union[BaseNode, AttributeAssociationNode]) -> None:
        """Writes a single node to a CSV file based on its datatype.

        :param node: The node to write
        """
        if self.graph_type != node.graph_type:
            raise AttributeError('type mismatch of writer (' + self.graph_type + ') and node (' + node.graph_type + ')')
        writer = self.writers[node.data_type]
        if writer is None:
            raise AttributeError('Writer not yet initialized')

        writer.writerow(node.to_csv_row())

    def write_edge(self, edge : Union[BaseEdge, AttributeAssociationEdge]) -> None:
        """Writes a single edge to a CSV file.

        :param edge: The edge to write
        """
        if self.graph_type != edge.graph_type:
            raise AttributeError('type mismatch of writer (' + self.graph_type + ') and node (' + edge.graph_type + ')')

        writer = self.writers['EdgeMain']
        if writer is None:
            raise AttributeError('Writer not yet initialized')

        writer.writerow(edge.to_csv_row())

    @staticmethod
    def write_graph(graph_dir : str, graph : Graph) -> None:
        """Writes a whole graph to a specified target directory in the form of CSV files.

        :param graph_dir: The directory the CSV files are written to
        :param graph: The graph that will be written
        """
        with GraphCSVWriter(graph_dir, graph.type) as writer:
            for node in graph.nodes:
                writer.write_node(node)

            for edge in graph.edges:
                writer.write_edge(edge)

class GraphDatabaseUtils:
    @staticmethod
    def get_neo4j_address(host: str = 'localhost', port: int = 7687, protocol : str = 'bolt') -> str:
        """Generates the address of a Neo4J DBMS with the given host, port and protocol.

        :param host: The host name where the Neo4J DBMS is running
        :param port: The port for the Neo4J Bolt protocol
        :param protocol: The protocol of the connection
        :return: Returns the address as string
        """
        if USE_PYODIDE:
            used_protocol = 'http'
        else:
            available_protocols = ['bolt', 'bolt+ssc', 'bolt+s', 'neo4j', 'neo4j+ssc', 'neo4j+s']
            if protocol not in available_protocols:
                raise AttributeError('Protocol "' + protocol + '" not recognized. Must be one of "'
                                      + '", "'.join(available_protocols) + '"')
            used_protocol = protocol
        return used_protocol + '://' + host + ':' + str(port)

    @staticmethod
    def _get_neo4j_http_request_body(queries : List[str]) -> str:
        """Generates the HTTP request body for a list of Neo4J Cypher queries

        :param queries: The Cypher queries
        :return: Returns the request body
        """
        return json.dumps({
            'statements': [{'statement' : query} for query in queries]
        })

    @staticmethod
    def _run_pyodide_neo4j_http_request(request_body: str, database: str, address: str = get_neo4j_address(),
                                        auth: Tuple[str, str] = ("neo4j", ""), transaction_id : Optional[int] = None,
                                        commit : bool = True) -> Tuple[bool, Dict[str, Any]]:
        """Send a Neo4J Cypher query as HTTP POST request, when the desktop version of graphxplore is used

        :param request_body: The body of the POST request
        :param database: The database the Cypher query should be sent to
        :param address: The address of the Neo4J DBMS
        :param auth: The authentication of the Neo4J DBMS
        :param transaction_id: The ID of an already existing transaction, defaults to None
        :param commit: If ``True`` the query will directly be committed. Should only be used for singular queries or to
            commit a whole transaction
        :return: Returns if the request was successful, and the response data
        """
        query_address = address + '/db/' + database + '/tx' + ('/' + str(transaction_id) if transaction_id else '') + ('/commit' if commit else '')
        headers = {
            'Accept': 'application/json;charset=UTF-8',
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + base64.b64encode(':'.join(auth).encode('utf8')).decode('ascii')
        }
        req = XMLHttpRequest.new()
        req.open("POST", query_address, False)
        for header, value in headers.items():
            req.setRequestHeader(header, value)
        blob = Blob.new([request_body], {type: 'application/json'})
        req.send(blob)
        return_data = json.loads(req.response)
        return (200 <= req.status <= 299), return_data

    @staticmethod
    def test_connection(address: str = get_neo4j_address(), auth : Tuple[str, str] = ("neo4j", "")) -> None:
        """Tests if a connection to a Neo4J DBMS is possible with the given host, bolt (Neo4J protocol) port and
        credentials. Raises an exception if the connection could not be established

        :param address: The address of the Neo4J DBMS
        :param auth: username and password to access the Neo4j DBMS
        """
        if USE_PYODIDE:
            try:
                query = 'CALL db.ping()'
                request_body = GraphDatabaseUtils._get_neo4j_http_request_body([query])
                ok, data = GraphDatabaseUtils._run_pyodide_neo4j_http_request(request_body, 'system', address, auth)
            except pyodide.ffi.JsException:
                raise AttributeError('Could not connect to Neo4J DBMS under address "' + address + '"')
            if not ok:
                raise AttributeError(
                'Could not connect to Neo4J DBMS under address "' + address + '" with given credentials')
        else:
            try:
                with GraphDatabase.driver(address, auth=auth) as driver:
                    driver.verify_connectivity()
            except (exceptions.Neo4jError, exceptions.DriverError, ValueError):
                raise AttributeError('Could not connect to Neo4J DBMS under address "' + address + '" with given credentials')

    @staticmethod
    def execute_query(query : str, database : str, address: str = get_neo4j_address(),
                      auth : Tuple[str, str] = ("neo4j", "")) -> List[Dict[str, Any]]:
        """Execute a single Cypher query and retrieve the results. Raises an exception if the query fails

        :param query: The Cypher query
        :param database: The Neo4J database to query
        :param address: The address of the Neo4J DBMS
        :param auth: The authentication of the Neo4J DBMS
        :return: Returns a list of dictionaries, one for each returned record
        """
        if USE_PYODIDE:
            try:
                request_body = GraphDatabaseUtils._get_neo4j_http_request_body([query])
                ok, data = GraphDatabaseUtils._run_pyodide_neo4j_http_request(
                    request_body, database, address, auth, commit=True)

                if not ok or len(data['errors']) > 0:
                    raise AttributeError('Query failed, error was: ' + ': '.join(data['errors'][0].values()))

                keys = data['results'][0]['columns']
                result = []
                for row in data['results'][0]['data']:
                    result.append(dict(zip(keys, row['row'])))
                return result
            except pyodide.ffi.JsException as error:
                raise AttributeError(
                    'Could not execute Cypher query, error was: ' + str(error))
        else:
            try:
                with GraphDatabase.driver(address, auth=auth) as driver:
                    records, summary, keys = driver.execute_query(query, database_=database)
                    return [record.data() for record in records]

            except (exceptions.Neo4jError, exceptions.DriverError) as error:
                raise AttributeError(
                    'Could not execute Cypher query, error was: ' + str(error))

    @staticmethod
    def get_existing_databases(address: str = get_neo4j_address(), auth : Tuple[str, str] = ("neo4j", "")) -> List[str]:
        """Retrieves the names of all databases existing in a Neo4J DBMS (except the "system" database). Raises an
        exception if the connection could not be established. Note that existing database will be listed, even if they
        are offline.

        :param address: The address of the Neo4J DBMS
        :param auth: username and password to access the Neo4j DBMS
        :return: Returns a list of all database names
        """
        GraphDatabaseUtils.test_connection(address, auth)
        records = GraphDatabaseUtils.execute_query(query='SHOW DATABASES', database='system', address=address,
                                                   auth=auth)
        return [record['name'] for record in records if record['name'] != 'system' and record['currentStatus'] == 'online']

    @staticmethod
    def check_graph_type_of_db(db_name: str, address: str = get_neo4j_address(),
                               auth: Tuple[str, str] = ("neo4j", "")) -> GraphType:
        """Retrieves the :class:`GraphType` of a given Neo4J database by checking all labels found in the database and
        checking for ``BaseNodeType.Key``, :class:`~graphxplore.Basis.AttributeAssociationGraph.DistinctionLabel`,
        :class:`~graphxplore.Basis.AttributeAssociationGraph.FrequencyLabel`. Raises an exception if the
        connection could not be established, the database does not exist in the DBMS, or the type of database is not
        recognized

        :param db_name: The database name
        :param address: The address of the Neo4J DBMS
        :param auth: username and password to access the Neo4j DBMS
        :return: Returns the type of graph
        """
        if db_name not in GraphDatabaseUtils.get_existing_databases(address, auth):
            raise AttributeError('Database "' + db_name + '" not found in Neo4J DBMS')

        records = GraphDatabaseUtils.execute_query(query='CALL db.labels()', database=db_name, address=address,
                                                   auth=auth)
        for record in records:
            label = record['label']
            if label == BaseNodeType.Key:
                return GraphType.Base
            if label in FrequencyLabel._value2member_map_:
                return GraphType.AttributeAssociation
        raise AttributeError('Graph type of database "' + db_name + '" not recognized')

    @staticmethod
    def database_contains_labels(db_name: str, labels : Iterable[str], address: str = get_neo4j_address(),
                                 auth: Tuple[str, str] = ("neo4j", "")) -> bool:
        """Checks if the nodes of a given database contain all labels specified in ``labels``

        :param db_name: The name of the database
        :param labels: The list of labels that should be contained
        :param address: The address of the Neo4J DBMS
        :param auth: username and password to access the Neo4j DBMS
        :return: Returns True, if all labels are contained
        """
        if db_name not in GraphDatabaseUtils.get_existing_databases(address, auth):
            raise AttributeError('Database "' + db_name + '" not found in Neo4J DBMS')

        found_labels = set()
        records = GraphDatabaseUtils.execute_query(query='CALL db.labels()', database=db_name, address=address,
                                                   auth=auth)
        for record in records:
            found_labels.add(record['label'])
        for label in labels:
            if label not in found_labels:
                return False
        return True

    @staticmethod
    def get_nof_edges_in_database(db_name: str, address: str = get_neo4j_address(),
                                  auth: Tuple[str, str] = ("neo4j", "")) -> int:
        """Returns the number of edges stored in a Neo4J database

        :param db_name: The name of the database
        :param address: The address of the Neo4J DBMS
        :param auth: username and password to access the Neo4j DBMS
        :return: Returns the number of edges
        """
        if db_name not in GraphDatabaseUtils.get_existing_databases(address, auth):
            raise AttributeError('Database "' + db_name + '" not found in Neo4J DBMS')

        query = 'MATCH ()-[r]->() RETURN count(r) as count'
        records = GraphDatabaseUtils.execute_query(query=query, database=db_name, address=address,
                                                   auth=auth)
        return records[0]['count']

    @staticmethod
    def get_node_write_cypher_statement(node : Union[BaseNode, AttributeAssociationNode], separate_params: bool = False,
                                        use_create: bool = True) -> Union[str, Tuple[str, Dict[str, Any]]]:
        """Generates a Cypher CREATE or MERGE statement to insert a single node into a Neo4J database

        :param node: The node to insert
        :param use_create: If ``True``, a CREATE statement is generated, else a MERGE statement
        :param separate_params: If ``True``, a separate dict of parameter/values is generated and parameters are added
            as variables with a preceding $ character
        :return: Returns the Cypher statement with or without parameter/value dictionary
        """
        labels, parameters = node.data_for_cypher_write_query()
        query = 'CALL apoc.'
        query += 'create' if use_create else 'merge'
        if separate_params:
            query += ('.node($labels, {' + ', '.join((parameter + ': $' + parameter for parameter in parameters))
                      + '}) YIELD node RETURN id(node) AS id')
            parameters['labels'] = labels
            return query, parameters
        else:
            query += ('.node(' + GraphDatabaseUtils.__parameter_to_string_for_query(labels) + ', {'
                      + ', '.join((param + ': ' + GraphDatabaseUtils.__parameter_to_string_for_query(value)
                                   for param, value in parameters.items()))
                      + '}) YIELD node RETURN id(node) AS id')
            return query

    @staticmethod
    def get_edge_write_cypher_statement(edge: Union[BaseEdge, AttributeAssociationEdge],
                                        node_id_mapping : Dict[int, int],
                                        separate_params: bool = False) -> Union[str, Tuple[str, Dict[str, Any]]]:
        """Generates a Cypher statement to insert a single edge into a Neo4J database given its edge type and
        parameters. Additionally, the incident nodes are matched prior to the merge by their internal database IDs.

        :param edge: The edge to insert
        :param node_id_mapping: A dictionary containing pairs of graphxplore node ID and associated internal node ID of
            the Neo4J database
        :param separate_params: If ``True``, a separate dict of parameter/values is generated and parameters are added
            as variables with a preceding $ character
        :return: Returns the Cypher statement with or without parameter/value dictionary
        """
        if edge.source not in node_id_mapping:
            raise AttributeError('Source node ID ' + str(edge.source) + ' not in given dictionary')

        if edge.target not in node_id_mapping:
            raise AttributeError('Target node ID ' + str(edge.target) + ' not in given dictionary')
        edge_type, parameters = edge.data_for_cypher_write_query()
        node_literals = ['s', 't']
        if separate_params:
            query = ' '.join(('MATCH(' + literal + ') WHERE id(' + literal + ')=$id_' + literal
                              for literal in node_literals))
            query += (' CALL apoc.create.relationship(' + node_literals[0] + ', $edge_type, {'
                      + ', '.join((parameter + ': $' + parameter for parameter in parameters)) + '}, '
                      + node_literals[1] + ') YIELD rel RETURN id(rel) as id')
            parameters['edge_type'] = edge_type
            parameters['id_' + node_literals[0]] = node_id_mapping[edge.source]
            parameters['id_' + node_literals[1]] = node_id_mapping[edge.target]
            return query, parameters
        else:
            query = ' '.join(('MATCH(' + literal + ') WHERE id(' + literal + ')='
                              + str(node_id_mapping[edge.source if literal == 's' else edge.target])
                              for literal in node_literals))
            query += (' CALL apoc.create.relationship(' + node_literals[0] + ', '
                      + GraphDatabaseUtils.__parameter_to_string_for_query(edge_type) + ', {'
                      + ', '.join((param + ': ' + GraphDatabaseUtils.__parameter_to_string_for_query(value)
                                   for param, value in parameters.items())) + '}, '
                      + node_literals[1] + ') YIELD rel RETURN id(rel) as id')
            return query

    @staticmethod
    def __parameter_to_string_for_query(param_value : Any) -> str:
        """Transforms a parameter value of to string for adding to a Neo4J Cypher statement

        :param param_value: The parameter value to transform to string
        :return: Returns the result string
        """
        if isinstance(param_value, list):
            clean_list_vals = (GraphDatabaseUtils.__parameter_to_string_for_query(list_val) for list_val in param_value)
            return '[' + ', '.join(clean_list_vals) + ']'
        if isinstance(param_value, str):
            return "'" + param_value + "'"
        if isinstance(param_value, float) and math.isnan(param_value):
            return 'NaN'
        if isinstance(param_value, float) and math.isinf(param_value):
            return 'Inf' if param_value > 0 else '-Inf'
        return str(param_value)

class GraphDatabaseWriter:
    """This class writes nodes and edges, and a whole :class:`Graph` object to a Neo4J database.
    WARNING: This class is not suited for very large graphs, since all nodes and edges are held in memory and the
    neo4j python interface is not designed for large bulk imports. In case of very large graphs please write your graph
    to CSV with :class:`GraphCSVWriter` and then import the CSVs using the "neo4j admin import" tool.

    :param db_name: The name of the database the data is written to
    :param overwrite: if `True`, database `db_name` will be overwritten if already exists
    :param address: The address of the Neo4J DBMS
    :param auth: username and password to access the Neo4j DBMS
    """
    def __init__(self, graph_type : GraphType, db_name : str, overwrite : bool = False,
                 address: str = GraphDatabaseUtils.get_neo4j_address(), auth : Tuple[str, str] = ("neo4j", "")):
        self.graph_type = graph_type
        self.db_name = db_name
        self.address = address
        self.auth = auth
        self.overwrite = overwrite
        self.nodes_dict = {}
        self.edges = []

    def write_node(self, node : Union[BaseNode, AttributeAssociationNode]) -> None:
        """Stores a single node for insertion into the Neo4J database. It will be cached and later written
        to the database

        :param node: The node to write
        """
        if self.graph_type != node.graph_type:
            raise AttributeError('type mismatch of writer (' + self.graph_type + ') and node (' + node.graph_type + ')')
        self.nodes_dict[node.node_id] = node

    def write_edge(self, edge : Union[BaseEdge, AttributeAssociationEdge]) -> None:
        """Stores a single edge for insertion into the Neo4J database. It will be cached and later written
        to the database

        :param edge: The edge to write
        """
        if self.graph_type != edge.graph_type:
            raise AttributeError('type mismatch of writer (' + self.graph_type + ') and node (' + edge.graph_type + ')')
        self.edges.append(edge)

    def __enter__(self):
        GraphDatabaseUtils.test_connection(self.address, self.auth)
        db_exists = self.db_name in GraphDatabaseUtils.get_existing_databases(self.address, self.auth)
        if not self.overwrite and db_exists:
            raise AttributeError('Graph database already exists. If you really want to overwrite it, you have to '
                                 'set the flag "overwrite" to True')

        if db_exists:
            print('Overwriting content of existing database "' + self.db_name + '"')
        GraphDatabaseUtils.execute_query(query='CREATE OR REPLACE DATABASE ' + self.db_name + ' WAIT 10 SECONDS',
                                         database='system', address=self.address, auth=self.auth)
        return self

    def _write_objects_neo4j_http(self, write_nodes : bool,
                                  node_id_dict: Optional[Dict[int, int]]) -> Optional[Dict[int, int]]:
        """Write nodes or edges to the database via HTTP requests. If edges are written ``node_id_dict``
        must be specified. For nodes, it can be ``None``

        :param write_nodes: Flag which specifies if nodes or edges should be written
        :param node_id_dict: Dictionary of graphxplore node ID to Neo4J internal node ID, or ``None``
        :return: Returns the dictionary of graphxplore node ID to Neo4J internal node ID, if nodes were written, or
            ``None`` if edges were written
        """
        try:
            curr_queries = []
            chunk_size = 10000
            curr_idx = 0

            objects = list(self.nodes_dict.values()) if write_nodes else self.edges

            node_db_ids = []
            counter = 0

            # write objects in chunks
            while curr_idx < len(objects):
                curr_end = min(curr_idx + chunk_size, len(objects))
                empty_body = GraphDatabaseUtils._get_neo4j_http_request_body([])
                ok, data = GraphDatabaseUtils._run_pyodide_neo4j_http_request(empty_body, self.db_name, self.address,
                                                                              self.auth, commit=False)
                if not ok or len(data['errors']) > 0:
                    raise AttributeError('Opening transaction for writing graph failed, error was: '
                                         + ': '.join(data['errors'][0].values()))
                transaction_str = data['commit']
                pattern = re.compile(r'(?<=/tx/)\d+(?=/commit)')
                matches = pattern.findall(transaction_str)
                if len(matches) != 1:
                    raise AttributeError('Writing graph failed, could not retrieve transaction ID')
                transaction_id = int(matches[0])
                for idx in range(curr_idx, curr_end):
                    if write_nodes:
                        query = GraphDatabaseUtils.get_node_write_cypher_statement(
                            objects[idx], separate_params=False)
                    else:
                        query = GraphDatabaseUtils.get_edge_write_cypher_statement(
                            objects[idx], node_id_dict, separate_params=False)
                    curr_queries.append(query)
                request_body = GraphDatabaseUtils._get_neo4j_http_request_body(curr_queries)
                ok, data = GraphDatabaseUtils._run_pyodide_neo4j_http_request(
                    request_body, self.db_name, self.address, self.auth, transaction_id=transaction_id, commit=False)

                if not ok or len(data['errors']) > 0:
                    print(request_body)
                    raise AttributeError('Writing graph failed, error was: '
                                         + ': '.join(data['errors'][0].values()))
                if write_nodes:
                    for row in data['results']:
                        node_db_ids.append(row['data'][0]['row'][0])

                curr_queries = []
                curr_idx = curr_end

                # commit batch of objects
                empty_body = GraphDatabaseUtils._get_neo4j_http_request_body([])
                ok, data = GraphDatabaseUtils._run_pyodide_neo4j_http_request(
                    empty_body, self.db_name, self.address, self.auth, transaction_id=transaction_id, commit=True)
                if not ok or len(data['errors']) > 0:
                    raise AttributeError('Writing graph failed, could not commit transaction. Error was: '
                                         + ': '.join(data['errors'][0].values()))
                counter += 1
                print('Wrote chunk '+ str(counter))

            if write_nodes:
                if len(node_db_ids) != len(objects):
                    raise AttributeError('Length of node db IDS:' + str(len(node_db_ids)) + ', but number of nodes is ' + str(len(objects)))
                return dict(zip((node.node_id for node in objects), node_db_ids))
            else:
                return None

        except pyodide.ffi.JsException as error:
            raise AttributeError('Writing graph failed, error was: ' + str(error))

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('Writing graph to database')
        if USE_PYODIDE:
            print('Writing nodes')
            node_id_dict = self._write_objects_neo4j_http(write_nodes=True, node_id_dict=None)
            print('Writing edges')
            self._write_objects_neo4j_http(write_nodes=False, node_id_dict=node_id_dict)
        else:
            try:
                with GraphDatabase.driver(self.address, auth=self.auth) as driver:
                    with driver.session(database=self.db_name) as session:
                        with session.begin_transaction() as tx:
                            # combine statements with the same query
                            query_params = collections.defaultdict(list)
                            for node in self.nodes_dict.values():
                                query, params = GraphDatabaseUtils.get_node_write_cypher_statement(
                                    node, separate_params=True)
                                query_params[query].append((params, node.node_id))
                            node_id_mapping = {}
                            for query, param_id_batch in query_params.items():
                                copied_query = query.replace('$', 'entry.')
                                copied_query = 'WITH $batch AS batch UNWIND batch AS entry ' + copied_query
                                param_batch = [entry[0] for entry in param_id_batch]
                                records = tx.run(copied_query, {'batch': param_batch})
                                db_ids = [entry['id'] for entry in records]
                                for idx in range(len(param_id_batch)):
                                    node_id_mapping[param_id_batch[idx][1]] = db_ids[idx]

                            query_params = collections.defaultdict(list)
                            for edge in self.edges:
                                query, params = GraphDatabaseUtils.get_edge_write_cypher_statement(
                                    edge, node_id_mapping, separate_params=True)
                                query_params[query].append(params)
                            for query, param_batch in query_params.items():
                                copied_query = query.replace('$', 'entry.')
                                copied_query = 'WITH $batch AS batch UNWIND batch AS entry ' + copied_query
                                tx.run(copied_query, {'batch': param_batch})
                            tx.commit()
            except (exceptions.Neo4jError, exceptions.DriverError) as error:
                raise AttributeError('Failed to write graph to database, error was: ' + str(error))



    @staticmethod
    def write_graph(db_name: str, graph: Graph, overwrite: bool = False,
                    address: str = GraphDatabaseUtils.get_neo4j_address(),
                    auth: Tuple[str, str] = ("neo4j", "")) -> None:
        """Writes a :class:`Graph` object to a Neo4J database.

        :param db_name: The name of the database the graph is written to
        :param graph: The graph to write
        :param overwrite: if `True`, database `db_name` will be overwritten if already exists
        :param address: The address of the Neo4J DBMS
        :param auth: username and password to access the Neo4j DBMS
        """
        with GraphDatabaseWriter(graph.type, db_name, overwrite, address, auth) as writer:
            for node in graph.nodes:
                writer.write_node(node)
            for edge in graph.edges:
                writer.write_edge(edge)


class RelationalDataIODevice:
    """This class reads and writes relational table data either from/to a directory as CSV files, or a dict in Python

    :param data_location: A directory path, or a dictionary of table name (without .csv extension) and list of
        table row dicts
    :param table: The current table to consider. Either ``table`` + '.csv' must be in specified directory path, or
        as key in the dict
    :param write: bool for write or read access
    :param header: The header to write in the csv. Can be omitted, if ``write`` is ``False``
    :param file_encoding: The file encoding of the CSV file to read. Can be omitted, if ``write`` is ``True``, or
        data dict is specified
    :param delimiter: The delimiter of the CSV file to read. Can be omitted, if ``write`` is ``True``, or
        data dict is specified
    """
    def __init__(self, data_location: Union[str, Dict[str, List[Dict[str, str]]]], table : str, write: bool = False,
                 header: Optional[List[str]] = None, file_encoding: Optional[str] = None,
                 delimiter: Optional[str] = None):
        """Constructor method
        """
        self.check_data_location(data_location, write)
        if not write:
            if table not in self.get_available_table_names(data_location):
                if isinstance(data_location, str):
                    raise AttributeError('Table "' + table + '" does not exist in directory "' + data_location
                                         + '" at path "' + os.path.join(data_location, table + '.csv') + '"')
                else:
                    raise AttributeError('Table "' + table + '" does not exist in data directory')
        self.data_location = data_location
        self.table = table
        self.write = write
        self.file_encoding = file_encoding
        self.delimiter = delimiter
        self.file = None
        self.reader = None
        self.writer = None
        if self.write and isinstance(data_location, str) and header is None:
            raise AttributeError('For writing table "' + table + '" you need to specify a CSV header')
        self.header = header

    def __enter__(self):
        if isinstance(self.data_location, str):
            mode = 'w' if self.write else 'r'
            table_path = os.path.join(self.data_location, self.table + '.csv')
            file_enc = self.file_encoding if self.file_encoding is not None else BaseUtils.detect_file_encoding(table_path)
            self.file = open(table_path, encoding=file_enc, mode=mode).__enter__()
            if self.write:
                self.writer = csv.DictWriter(self.file, fieldnames=self.header,
                                             delimiter=self.delimiter if self.delimiter is not None else ',')
                self.writer.writeheader()
            else:
                if self.delimiter is None:
                    try:
                        dialect = csv.Sniffer().sniff(self.file.read(100000), delimiters=',;|\t ')
                        self.file.seek(0)
                        self.reader = csv.DictReader(self.file, dialect=dialect)
                    except csv.Error:
                        self.file.seek(0)
                        self.reader = csv.DictReader(self.file)
                else:
                    self.reader = csv.DictReader(self.file, delimiter=self.delimiter)
        else:
            if self.write:
                if self.table not in self.data_location:
                    self.data_location[self.table] = []
                self.writer = self.data_location[self.table]
            else:
                self.reader = iter(self.data_location[self.table])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(self.data_location, str):
            self.file.__exit__(exc_type, exc_val, exc_tb)

    def __iter__(self):
        return self

    def __next__(self) -> Dict[str, str]:
        return next(self.reader)

    def writerow(self, row : Dict[str, Union[str, int, float, None]]):
        """Write a single table row to the output

        :param row: The data row as a dict of variable name and value
        """
        if not self.write:
            raise AttributeError('Cannot write, because IO device was initialized as read-only')
        if isinstance(self.data_location, str):
            self.writer.writerow(row)
        else:
            casted_row = {}
            for key in self.header:
                if key not in row:
                    raise AttributeError('There is not value for key "' + key + '" in input data')
                casted_val = '' if row[key] is None else str(row[key])
                casted_row[key] = casted_val
            self.writer.append(casted_row)

    def get_header(self) -> List[str]:
        """Get the currently used header of the table

        :return: Returns the header as list of strings
        """
        if self.header is not None:
            return self.header
        if isinstance(self.data_location, str):
            return list(self.reader.fieldnames)
        else:
            return list(self.data_location[self.table][0].keys())

    @staticmethod
    def check_data_location(data_location: Union[str, Dict[str, List[Dict[str, str]]]], write: bool = False):
        """Check if the data location exists as path, if it is a string, or if there is at least one table present in
        the data dict if ``write`` is ``False``

        :param data_location: A directory path, or a dictionary of table name (without .csv extension) and list of
            table row dicts
        :param write: bool for write or read access
        """
        if isinstance(data_location, str):
            if not os.path.isdir(data_location):
                raise AttributeError('"' + data_location + '" is not a valid directory')
        elif not write:
            if len(data_location) == 0:
                raise AttributeError('No CSV tables specified in data dictionary')

    @staticmethod
    def get_available_table_names(data_source: Union[str, Dict[str, List[Dict[str, str]]]]) -> List[str]:
        """Retrieves all table names (without .csv extension) from a directory path, or all keys from a data dictionary

        :param data_source: A directory path, or a dictionary of table name (without .csv extension) and list of
            table row dicts
        :return: Returns the found table names as a list of strings
        """
        RelationalDataIODevice.check_data_location(data_source)
        if isinstance(data_source, str):
            return sorted([table.replace('.csv', '') for table in os.listdir(data_source) if table.endswith('.csv')])
        else:
            return sorted(data_source.keys())