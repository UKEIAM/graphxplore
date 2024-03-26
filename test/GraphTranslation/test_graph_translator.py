import os.path
import pathlib
import csv
import warnings
import pytest
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.MetaDataHandling import MetaData
from graphxplore.GraphTranslation import GraphTranslator
from graphxplore.Basis import GraphCSVReader, GraphDatabaseWriter, GraphType, GraphDatabaseUtils
TEST_DIR = os.path.join(ROOT_DIR, 'test')
sys.path.append(TEST_DIR)
import neo4j_test_config

def test_graph_generation():
    data_dir = os.path.join(TEST_DIR, 'GraphTranslation', 'test_data')
    out_dir = os.path.join(TEST_DIR, 'GraphTranslation', 'test_output')
    meta_path = os.path.join(TEST_DIR, 'MetaDataHandling', 'test_output', 'meta.json')
    meta = MetaData.load_from_json(meta_path)
    graph_translator = GraphTranslator(meta)
    graph_translator.transform_to_graph(data_dir, out_dir)
    reader = GraphCSVReader(out_dir, GraphType.Base)
    reloaded_graph = reader.read_graph()
    reloaded_data = {'String' : [[':ID', ':LABEL', 'name', 'value', 'description']],
                     'Integer' : [[':ID', ':LABEL', 'name', 'value:long', 'description']],
                     'Decimal' : [[':ID', ':LABEL', 'name', 'value:double', 'description']],
                     'Bin' : [[':ID', ':LABEL', 'name', 'value', 'description', 'refRange:double[]']],
                     'Edge' : [[':START_ID', ':END_ID', ':TYPE']]}
    for node in reloaded_graph.nodes:
        row = node.to_csv_row()
        string_row = [str(x) for x in row]
        reloaded_data[node.data_type].append(string_row)

    for edge in reloaded_graph.edges:
        row = edge.to_csv_row()
        string_row = [str(x) for x in row]
        reloaded_data['Edge'].append(string_row)

    with open(os.path.join(out_dir, 'Node_Table_String.csv')) as node_file:
        reader = csv.reader(node_file)
        actual = [line for line in reader]
        expected = [[':ID', ':LABEL', 'name', 'value', 'description'],
                     ['3', 'primary_table;Attribute', 'STRING_ATTR', 'Text', 'contains text'],
                     ['7',
                      'primary_table;Attribute',
                      'STRING_ATTR',
                      'AnotherText\nMoreText',
                      'contains text'],
                     ['11',
                      'primary_table;Attribute',
                      'STRING_ATTR',
                      'TextWithoutQuotes',
                      'contains text'],
                     ['17',
                      'secondary_table;Attribute',
                      'ATTR_WITH_EMPTY',
                      'default value',
                      'weird variable'],
                     ['20',
                      'secondary_table;Attribute',
                      'ATTR_WITH_EMPTY',
                      'NotEmpty',
                      'weird variable']]
        assert actual == expected
        assert reloaded_data['String'] == expected

    with open(os.path.join(out_dir, 'Node_Table_Integer.csv')) as node_file:
        reader = csv.reader(node_file)
        actual = [line for line in reader]
        expected = [[':ID', ':LABEL', 'name', 'value:long', 'description'],
                     ['1', 'primary_table;Key', 'PRIMARY', '1', 'primary key'],
                     ['2', 'primary_table;Attribute', 'ROW_ID', '0', 'irrelevant index'],
                     ['5', 'primary_table;Key', 'PRIMARY', '2', 'primary key'],
                     ['6', 'primary_table;Attribute', 'ROW_ID', '1', 'irrelevant index'],
                     ['9', 'primary_table;Key', 'PRIMARY', '3', 'primary key'],
                     ['10', 'primary_table;Attribute', 'ROW_ID', '2', 'irrelevant index'],
                     ['16', 'secondary_table;Key', 'OWN_PRIMARY', '0', 'primary key'],
                     ['19', 'secondary_table;Key', 'OWN_PRIMARY', '1', 'primary key'],
                     ['22', 'secondary_table;Key', 'OWN_PRIMARY', '2', 'primary key'],
                     ['24', 'primary_table;Key', 'PRIMARY', '0', 'primary key'],
                     ['25', 'secondary_table;Key', 'OWN_PRIMARY', '3', 'primary key']]
        assert actual == expected
        assert reloaded_data['Integer'] == expected

    with open(os.path.join(out_dir, 'Node_Table_Decimal.csv')) as node_file:
        reader = csv.reader(node_file)
        actual = [line for line in reader]
        expected = [[':ID', ':LABEL', 'name', 'value:double', 'description'],
                     ['4', 'primary_table;Attribute', 'FLOAT_ATTR', '0.5', ''],
                     ['8', 'primary_table;Attribute', 'MIXED_ATTR', '0.2', ''],
                     ['12', 'primary_table;Attribute', 'FLOAT_ATTR', '1.0', ''],
                     ['13', 'primary_table;Attribute', 'MIXED_ATTR', '2.0', ''],
                     ['18', 'secondary_table;Attribute', 'FLOAT_INT_ATTR', '1.0', ''],
                     ['21', 'secondary_table;Attribute', 'FLOAT_INT_ATTR', '1.01', ''],
                     ['23', 'secondary_table;Attribute', 'FLOAT_INT_ATTR', '2.0', '']]
        assert actual == expected
        assert reloaded_data['Decimal'] == expected

    with open(os.path.join(out_dir, 'Node_Table_Bin.csv')) as node_file:
        reader = csv.reader(node_file)
        actual = [line for line in reader]
        expected = [[':ID',
                      ':LABEL',
                      'name',
                      'value',
                      'description',
                      'refRange:double[]'],
                    ['14', 'primary_table;AttributeBin', 'FLOAT_ATTR', 'normal', '', '0.0;0.5'],
                    ['15', 'primary_table;AttributeBin', 'FLOAT_ATTR', 'high', '', '0.0;0.5']]
        assert actual == expected
        assert reloaded_data['Bin'] == expected

    with open(os.path.join(out_dir, 'Relationship_Table_Main.csv')) as edge_file:
        reader = csv.reader(edge_file)
        actual = [line for line in reader]

        expected = [[':START_ID', ':END_ID', ':TYPE'],
                     ['1', '2', 'HAS_ATTR_VAL'],
                     ['1', '3', 'HAS_ATTR_VAL'],
                     ['1', '4', 'HAS_ATTR_VAL'],
                     ['5', '6', 'HAS_ATTR_VAL'],
                     ['5', '7', 'HAS_ATTR_VAL'],
                     ['5', '4', 'HAS_ATTR_VAL'],
                     ['5', '8', 'HAS_ATTR_VAL'],
                     ['9', '10', 'HAS_ATTR_VAL'],
                     ['9', '11', 'HAS_ATTR_VAL'],
                     ['9', '12', 'HAS_ATTR_VAL'],
                     ['9', '13', 'HAS_ATTR_VAL'],
                     ['4', '14', 'ASSIGNED_BIN'],
                     ['12', '15', 'ASSIGNED_BIN'],
                     ['16', '17', 'HAS_ATTR_VAL'],
                     ['16', '18', 'HAS_ATTR_VAL'],
                     ['1', '16', 'CONNECTED_TO'],
                     ['19', '20', 'HAS_ATTR_VAL'],
                     ['19', '21', 'HAS_ATTR_VAL'],
                     ['1', '19', 'CONNECTED_TO'],
                     ['22', '17', 'HAS_ATTR_VAL'],
                     ['22', '23', 'HAS_ATTR_VAL'],
                     ['24', '22', 'CONNECTED_TO'],
                     ['25', '20', 'HAS_ATTR_VAL'],
                     ['25', '23', 'HAS_ATTR_VAL'],
                     ['5', '25', 'CONNECTED_TO']]

        assert actual == expected
        assert reloaded_data['Edge'] == expected

    csv_data = {}
    for csv_table in os.listdir(data_dir):
        if csv_table.endswith('.csv'):
            with open(os.path.join(data_dir, csv_table)) as file:
                reader = csv.DictReader(file)
                csv_data[csv_table.replace('.csv', '')] = [line for line in reader]
    graph_translator_from_dict = GraphTranslator(meta)
    graph_translator_from_dict.transform_to_graph(data_dir, out_dir)
    reader = GraphCSVReader(out_dir, GraphType.Base)
    reloaded_graph_from_dict = reader.read_graph()
    reloaded_data_from_dict = {'String': [[':ID', ':LABEL', 'name', 'value', 'description']],
                               'Integer': [[':ID', ':LABEL', 'name', 'value:long', 'description']],
                               'Decimal': [[':ID', ':LABEL', 'name', 'value:double', 'description']],
                               'Bin': [[':ID', ':LABEL', 'name', 'value', 'description', 'refRange:double[]']],
                               'Edge': [[':START_ID', ':END_ID', ':TYPE']]}
    for node in reloaded_graph_from_dict.nodes:
        row = node.to_csv_row()
        string_row = [str(x) for x in row]
        reloaded_data_from_dict[node.data_type].append(string_row)

    for edge in reloaded_graph_from_dict.edges:
        row = edge.to_csv_row()
        string_row = [str(x) for x in row]
        reloaded_data_from_dict['Edge'].append(string_row)
    assert reloaded_data == reloaded_data_from_dict

    if not neo4j_test_config.RUN_DB_TESTS:
        warnings.warn('GraphTranslation database query tests are not executed. If you want to execute them, '
                      'set the flag "RUN_DB_TESTS" in "test/neo4j_test_config.py"')
    else:

        if not neo4j_test_config.test_connectivity():
            pytest.fail('Neo4J DBMS for testing not available under given configuration. Check "test/neo4j_test_config.py"')
        else:
            address = neo4j_test_config.get_neo4j_address()
            GraphDatabaseWriter.write_graph('test', reloaded_graph, overwrite=True, address=address,
                                            auth=neo4j_test_config.NEO4J_AUTH)

            assert GraphDatabaseUtils.check_graph_type_of_db('test', address=address,
                                                             auth=neo4j_test_config.NEO4J_AUTH) == GraphType.Base

            assert GraphDatabaseUtils.database_contains_labels('test', meta.get_table_names(), address=address,
                                                               auth=neo4j_test_config.NEO4J_AUTH)

            assert not GraphDatabaseUtils.database_contains_labels('test', meta.get_table_names() + ['invalid'],
                                                                   address=address,
                                                                   auth=neo4j_test_config.NEO4J_AUTH)

            assert GraphDatabaseUtils.get_nof_edges_in_database('test', address=address,
                                                                auth=neo4j_test_config.NEO4J_AUTH) == 25

            query = 'MATCH (n) RETURN count(n) as count'
            result = GraphDatabaseUtils.execute_query(query, 'test', address, neo4j_test_config.NEO4J_AUTH)
            assert result[0]['count'] == 25

            query = 'MATCH (n {name:"FLOAT_ATTR", value:"normal"}) RETURN n.refRange as range'
            result = GraphDatabaseUtils.execute_query(query, 'test', address, neo4j_test_config.NEO4J_AUTH)
            assert result[0]['range'] == [0.0, 0.5]

if __name__ == '__main__':
    pytest.main()
