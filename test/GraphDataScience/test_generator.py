import math
import pathlib
import pytest
import os
import csv
import warnings
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.GraphDataScience import AttributeAssociationGraphGenerator
from graphxplore.Basis import GraphCSVWriter, GraphDatabaseWriter, GraphType, GraphDatabaseUtils
from graphxplore.Basis.BaseGraph import BaseNodeType
from graphxplore.Basis.AttributeAssociationGraph import AttributeAssociationNode, AttributeAssociationLabels

def test_invalid_arguments(neo4j_config):
    run_db_test, neo4j_address, neo4j_auth = neo4j_config
    if not run_db_test:
        warnings.warn('AttributeAssociationGraphGenerator database query tests are not executed. If you want to execute them, '
                      'set the flag "--run_neo4j_tests" when running pytest to "True"')
        dbms_test = False
    else:
        try:
            GraphDatabaseUtils.test_connection(neo4j_address, neo4j_auth)
            dbms_test = True
        except AttributeError:
            dbms_test = False
            pytest.fail(
                'Neo4J DBMS for testing not available under given configuration. Adjust parameters "--neo4j_host",'
                ' "--neo4j_port", "--neo4j_user" and/or "--neo4j_pwd"')
    if dbms_test:
        generator = AttributeAssociationGraphGenerator(db_name='invalid', group_selection={'group' : 'group_selection'},
                                                       address='invald://invalid')
        with pytest.raises(AttributeError) as exc:
            generator.generate_graph()
        assert str(exc.value) == ('Could not connect to Neo4J DBMS under address "invald://invalid" with given '
                                  'credentials')
        generator = AttributeAssociationGraphGenerator(db_name='test', group_selection={'group': 'group_selection'},
                                                       address=neo4j_address,
                                                       auth=('invalid', 'invalid'))
        with pytest.raises(AttributeError) as exc:
            generator.generate_graph()
        assert str(exc.value) == ('Could not connect to Neo4J DBMS under address "'
                                  + neo4j_address + '" with given credentials')
        generator = AttributeAssociationGraphGenerator(db_name='invalid', group_selection={'group': 'group_selection'},
                                                       address=neo4j_address, auth=neo4j_auth)
        with pytest.raises(AttributeError) as exc:
            generator.generate_graph()
        assert str(exc.value) == 'Database "invalid" does not exist under address "' + neo4j_address + '"'

        # it is assumed that the database "test" was already created via the "test_graph_translator.py" test script
        generator = AttributeAssociationGraphGenerator(db_name='test', group_selection={'group': 'group_selection'},
                                                       address=neo4j_address, auth=neo4j_auth)
        with pytest.raises(AttributeError) as exc:
            generator.generate_graph()
        assert str(exc.value) == 'Cypher query must use "x_0" as variable for the node ID of group primary keys'
        generator = AttributeAssociationGraphGenerator(db_name='test', group_selection={'group': 'match(x_0)'},
                                                       address=neo4j_address, auth=neo4j_auth)
        with pytest.raises(AttributeError) as exc:
            generator.generate_graph()
        assert str(exc.value) == 'Cypher query must end with "return id(<node variable>) as x_0"'

        generator = AttributeAssociationGraphGenerator(
            db_name='test', group_selection={'group': 'match(n) invalid Return id(n) as x_0'},
            address=neo4j_address, auth=neo4j_auth)
        with pytest.raises(AttributeError) as exc:
            generator.generate_graph()
        assert str(exc.value).startswith('Cypher query invalid: "match(n) invalid Return id(n) as x_0", error was: ')
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationGraphGenerator(db_name='test',
                                           group_selection={'group1': 'group_selection',
                                                            'group2': 'group_selection'},
                                           positive_group='group1')
    assert str(exc.value) == 'Either both or none of positive and negative group have be specified'

    with pytest.raises(AttributeError) as exc:
        AttributeAssociationGraphGenerator(db_name='test',
                                           group_selection={'group1': 'group_selection',
                                                            'group2': 'group_selection'},
                                           positive_group='invalid', negative_group='alsoInvalid')
    assert str(exc.value) == 'Positive group "invalid" not in listed groups'

    with pytest.raises(AttributeError) as exc:
        AttributeAssociationGraphGenerator(db_name='test',
                                           group_selection={'group1': 'group_selection',
                                                            'group2': 'group_selection'},
                                           frequency_thresholds=(0.2,0.1))
    assert str(exc.value) == ('Threshold for "frequent" nodes must be smaller or equal to threshold for '
                              '"highly frequent" nodes')
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationGraphGenerator(db_name='test',
                                           group_selection={'group1': 'group_selection',
                                                            'group2': 'group_selection'},
                                           frequency_thresholds=(2.0,0.1))
    assert str(exc.value) == 'Frequency thresholds must be smaller or equal to 1'
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationGraphGenerator(db_name='test',
                                           group_selection={'group1': 'group_selection',
                                                            'group2': 'group_selection'},
                                           increase_ratio_thresholds=(2.0,0.1))
    assert str(exc.value) == 'Conditional increase ratio thresholds must be larger or equal to 1'

def test_scores_and_write_with_one_group(neo4j_config):
    generator = AttributeAssociationGraphGenerator(db_name='test',
                                                   group_selection={'group1': 'group_selection'})
    generator.group_sizes = {'group1': 10}
    groups = ['group1']
    generator.nodes_with_count = {
        AttributeAssociationNode(1, AttributeAssociationLabels(('Test',), BaseNodeType.Attribute),
                                 'SomeAttr', 'val1', groups): {'group1': 5},
        AttributeAssociationNode(2, AttributeAssociationLabels(('Test',), BaseNodeType.Attribute),
                                 'OtherAttr', 'val2', groups): {'group1': 4}
    }

    generator.variable_counts = {
        'SomeAttr': {'group1': 9},
        'OtherAttr': {'group1': 8}
    }

    generator.node_pairs_with_intersection = {
        (1, 2): {'group1': 1}
    }

    generator._generate_metrics()

    graph = generator.result_graph

    out_dir = os.path.join(ROOT_DIR, 'test', 'GraphDataScience', 'test_output', 'generator')

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    GraphCSVWriter.write_graph(out_dir, graph)

    with open(os.path.join(out_dir, 'Node_Table_String.csv')) as node_file:
        reader = csv.reader(node_file)
        actual = []
        for line in reader:
            actual.append(line)
        expected = [[':ID',
                      ':LABEL',
                      'name',
                      'value',
                      'description',
                      'groups[]',
                      'count:long[]',
                      'missing:double[]',
                      'prevalence:double[]',
                      'prevalence_difference:double',
                      'prevalence_ratio:double'],
                     ['1',
                      'Test;Attribute;HighlyFrequent',
                      'SomeAttr',
                      'val1',
                      'NaN',
                      'group1 (10)',
                      '5',
                      '0.1',
                      '0.55556',
                      'nan',
                      'nan'],
                     ['2',
                      'Test;Attribute;HighlyFrequent',
                      'OtherAttr',
                      'val2',
                      'NaN',
                      'group1 (10)',
                      '4',
                      '0.2',
                      '0.5',
                      'nan',
                      'nan']]
        assert actual == expected

    with open(os.path.join(out_dir, 'Relationship_Table_Main.csv')) as edge_file:
        reader = csv.reader(edge_file)
        actual = []
        for line in reader:
            actual.append(line)
        expected = [[':START_ID',
                      ':END_ID',
                      ':TYPE',
                      'groups[]',
                      'co_occurrence:long[]',
                      'conditional_prevalence:double[]',
                      'conditional_increase:double[]',
                      'increase_ratio:double[]'],
                     ['1', '2', 'HIGH_RELATION', 'group1 (10)', '1', '0.2', '-0.3', '0.4'],
                     ['2', '1', 'HIGH_RELATION', 'group1 (10)', '1', '0.25', '-0.30556', '0.45']]
        assert actual == expected

    run_db_test, neo4j_address, neo4j_auth = neo4j_config

    if run_db_test:
        try:
            GraphDatabaseUtils.test_connection(neo4j_address, neo4j_auth)
            dbms_test = True
        except AttributeError:
            dbms_test = False
            pytest.fail(
                'Neo4J DBMS for testing not available under given configuration. Adjust parameters "--neo4j_host",'
                ' "--neo4j_port", "--neo4j_user" and/or "--neo4j_pwd"')

        if dbms_test:
            GraphDatabaseWriter.write_graph('test', graph, overwrite=True, address=neo4j_address, auth=neo4j_auth)

            assert GraphDatabaseUtils.check_graph_type_of_db(
                'test', address=neo4j_address, auth=neo4j_auth) == GraphType.AttributeAssociation

            assert GraphDatabaseUtils.get_nof_edges_in_database('test', address=neo4j_address, auth=neo4j_auth) == 2

            query = 'MATCH (n) RETURN count(n) as count'
            result = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
            assert result[0]['count'] == 2
            query = 'MATCH (n:Attribute {value:"val2"}) RETURN n.prevalence_ratio as ratio'
            result = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
            assert math.isnan(result[0]['ratio'])

def test_score_calculation_and_write(neo4j_config):
    generator = AttributeAssociationGraphGenerator(db_name='test',
                                                   group_selection={'group1' : 'group_selection',
                                                                    'group2' : 'group_selection'},
                                                   positive_group='group1', negative_group='group2')
    generator.group_sizes = {'group1' : 10, 'group2' : 8}
    groups = ['group1', 'group2']
    generator.nodes_with_count = {
        AttributeAssociationNode(1, AttributeAssociationLabels(('Test',), BaseNodeType.Attribute),
                                 'SomeAttr', 'val1', groups, positive_group='group1', negative_group='group2')
            : {'group1' : 5, 'group2' : 1},
        AttributeAssociationNode(2, AttributeAssociationLabels(('Test',), BaseNodeType.Attribute),
                                 'SomeAttr', 'val2', groups, positive_group='group1', negative_group='group2')
        : {'group1': 4, 'group2': 8},
        AttributeAssociationNode(3, AttributeAssociationLabels(('Test',), BaseNodeType.Attribute),
                                 'OtherAttr', 'val3', groups, positive_group='group1', negative_group='group2')
        : {'group1': 8, 'group2': 8},
        AttributeAssociationNode(4, AttributeAssociationLabels(('Test',), BaseNodeType.Attribute),
                                 'OtherAttr', 'val4', groups, positive_group='group1', negative_group='group2')
        : {'group1': 0, 'group2': 3},
        AttributeAssociationNode(5, AttributeAssociationLabels(('Test',), BaseNodeType.Attribute),
                                 'AnotherAttr', 'val5', groups, positive_group='group1', negative_group='group2')
        : {'group1': 6, 'group2': 7},
        AttributeAssociationNode(6, AttributeAssociationLabels(('Test',), BaseNodeType.Attribute),
                                 'AnotherAttr', 'val6', groups, positive_group='group1', negative_group='group2')
        : {'group1': 7, 'group2': 6}
    }

    generator.variable_counts = {
        'SomeAttr' : {'group1' : 9, 'group2' : 8},
        'OtherAttr' : {'group1' : 8, 'group2' : 8},
        'AnotherAttr' : {'group1' : 10, 'group2' : 7}
    }

    generator.node_pairs_with_intersection = {
        (1, 2) : {'group1' : 1, 'group2' : 1},
        (1, 5) : {'group1' : 3, 'group2' : 1},
        (3, 4): {'group1' : 0, 'group2' : 2},
        (5, 6) : {'group1' : 6, 'group2' : 5}
    }

    generator._generate_metrics()

    graph = generator.result_graph

    out_dir = os.path.join(ROOT_DIR, 'test', 'GraphDataScience', 'test_output', 'generator')

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    GraphCSVWriter.write_graph(out_dir, graph)

    with open(os.path.join(out_dir, 'Node_Table_String.csv')) as node_file:
        reader = csv.reader(node_file)
        actual = []
        for line in reader:
            actual.append(line)
        expected = [[':ID',
                      ':LABEL',
                      'name',
                      'value',
                      'description',
                      'groups[]',
                      'count:long[]',
                      'missing:double[]',
                      'prevalence:double[]',
                      'prevalence_difference:double',
                      'prevalence_ratio:double'],
                     ['1',
                      'Test;Attribute;HighlyRelated;HighlyFrequent',
                      'SomeAttr',
                      'val1',
                      'NaN',
                      'group1 (10)[+];group2 (8)[-]',
                      '5;1',
                      '0.1;0.0',
                      '0.55556;0.125',
                      '0.43056',
                      '4.44448'],
                     ['2',
                      'Test;Attribute;HighlyInverse;HighlyFrequent',
                      'SomeAttr',
                      'val2',
                      'NaN',
                      'group1 (10)[+];group2 (8)[-]',
                      '4;8',
                      '0.1;0.0',
                      '0.44444;1.0',
                      '0.55556',
                      '2.25002'],
                     ['3',
                      'Test;Attribute;Unrelated;HighlyFrequent',
                      'OtherAttr',
                      'val3',
                      'NaN',
                      'group1 (10)[+];group2 (8)[-]',
                      '8;8',
                      '0.2;0.0',
                      '1.0;1.0',
                      '0.0',
                      '1.0'],
                     ['4',
                      'Test;Attribute;HighlyInverse;Frequent',
                      'OtherAttr',
                      'val4',
                      'NaN',
                      'group1 (10)[+];group2 (8)[-]',
                      '0;3',
                      '0.2;0.0',
                      '0.0;0.375',
                      '0.375',
                      'inf'],
                     ['5',
                      'Test;Attribute;HighlyInverse;HighlyFrequent',
                      'AnotherAttr',
                      'val5',
                      'NaN',
                      'group1 (10)[+];group2 (8)[-]',
                      '6;7',
                      '0.0;0.125',
                      '0.6;1.0',
                      '0.4',
                      '1.66667'],
                     ['6',
                      'Test;Attribute;Inverse;HighlyFrequent',
                      'AnotherAttr',
                      'val6',
                      'NaN',
                      'group1 (10)[+];group2 (8)[-]',
                      '7;6',
                      '0.0;0.125',
                      '0.7;0.85714',
                      '0.15714',
                      '1.22449']]
        assert actual == expected

    with open(os.path.join(out_dir, 'Relationship_Table_Main.csv')) as edge_file:
        reader = csv.reader(edge_file)
        actual = []
        for line in reader:
            actual.append(line)
        expected = [[':START_ID',
                      ':END_ID',
                      ':TYPE',
                      'groups[]',
                      'co_occurrence:long[]',
                      'conditional_prevalence:double[]',
                      'conditional_increase:double[]',
                      'increase_ratio:double[]'],
                     ['1',
                      '2',
                      'HIGH_RELATION',
                      'group1 (10)[+];group2 (8)[-]',
                      '1;1',
                      '0.2;1.0',
                      '-0.24444;0.0',
                      '0.45;1.0'],
                     ['2',
                      '1',
                      'HIGH_RELATION',
                      'group1 (10)[+];group2 (8)[-]',
                      '1;1',
                      '0.25;0.125',
                      '-0.30556;0.0',
                      '0.45;1.0'],
                     ['1',
                      '5',
                      'LOW_RELATION',
                      'group1 (10)[+];group2 (8)[-]',
                      '3;1',
                      '0.6;1.0',
                      '0.0;0.0',
                      '1.0;1.0'],
                     ['5',
                      '1',
                      'LOW_RELATION',
                      'group1 (10)[+];group2 (8)[-]',
                      '3;1',
                      '0.5;0.14286',
                      '-0.05556;0.01786',
                      '0.89999;1.14288'],
                     ['3',
                      '4',
                      'MEDIUM_RELATION',
                      'group1 (10)[+];group2 (8)[-]',
                      '0;2',
                      '0.0;0.25',
                      '0.0;-0.125',
                      '1.0;0.66667'],
                     ['4',
                      '3',
                      'HIGH_RELATION',
                      'group1 (10)[+];group2 (8)[-]',
                      '0;2',
                      '0.0;0.66667',
                      '-1.0;-0.33333',
                      'nan;0.66667'],
                     ['5',
                      '6',
                      'HIGH_RELATION',
                      'group1 (10)[+];group2 (8)[-]',
                      '6;5',
                      '1.0;0.71429',
                      '0.3;-0.14285',
                      '1.42857;0.83334'],
                     ['6',
                      '5',
                      'HIGH_RELATION',
                      'group1 (10)[+];group2 (8)[-]',
                      '6;5',
                      '0.85714;0.83333',
                      '0.25714;-0.16667',
                      '1.42857;0.83333']]
        assert actual == expected

    run_db_test, neo4j_address, neo4j_auth = neo4j_config

    if run_db_test:
        try:
            GraphDatabaseUtils.test_connection(neo4j_address, neo4j_auth)
            dbms_test = True
        except AttributeError:
            dbms_test = False
            pytest.fail(
                'Neo4J DBMS for testing not available under given configuration. Adjust parameters "--neo4j_host",'
                ' "--neo4j_port", "--neo4j_user" and/or "--neo4j_pwd"')

        if dbms_test:
            GraphDatabaseWriter.write_graph('test', graph, overwrite=True, address=neo4j_address, auth=neo4j_auth)

            assert GraphDatabaseUtils.check_graph_type_of_db(
                'test', address=neo4j_address, auth=neo4j_auth) == GraphType.AttributeAssociation

            assert GraphDatabaseUtils.get_nof_edges_in_database('test', address=neo4j_address, auth=neo4j_auth) == 8

            query = 'MATCH (n) RETURN count(n) as count'
            result = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
            assert result[0]['count'] == 6
            query = 'MATCH (n:Attribute {value:"val2"}) RETURN n.prevalence_ratio as ratio'
            result = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
            assert result[0]['ratio'] == 2.25002
            query = 'MATCH (n:Attribute {value:"val4"}) RETURN n.prevalence_ratio as ratio'
            result = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
            assert result[0]['ratio'] == math.inf

if __name__ == '__main__':
    pytest.main()