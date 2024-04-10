import os
import pathlib
import pytest
import warnings
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.Basis import GraphOutputType, GraphDatabaseUtils
from graphxplore.MetaDataHandling import MetaDataGenerator, DataType
from graphxplore.GraphTranslation import GraphTranslator
from graphxplore.GraphDataScience import GroupSelector
from graphxplore.DataMapping import AggregatorType
from graphxplore.DataMapping.Conditionals import (StringOperator, StringOperatorType, AlwaysTrueOperator,
                                                  MetricOperatorType, MetricOperator, AggregatorOperator,
                                                  AndOperator, OrOperator, NegatedOperator)

def test_cypher_queries(neo4j_config):
    run_db_test, neo4j_address, neo4j_auth = neo4j_config
    if not run_db_test:
        warnings.warn('DashboardBuilder database query tests are not executed. If you want to execute them, '
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
    csv_dir = os.path.join(ROOT_DIR, 'test', 'GraphDataScience', 'test_data', 'group_selector')
    meta_gen = MetaDataGenerator(csv_dir)
    meta = meta_gen.gather_meta_data()
    graph_translator = GraphTranslator(meta)
    if dbms_test:
        graph_translator.transform_to_graph(csv_dir, 'test', GraphOutputType.Database, overwrite=True,
                                            address=neo4j_address, auth=neo4j_auth)
    selector = GroupSelector('root', meta)
    query = selector.get_cypher_query()
    assert query == 'match (x_0:root {name:"root_pk"}) where x_0:Key\nwith x_0\nreturn id(x_0) as x_0'
    if dbms_test:
        cursor = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert len(cursor) == 3
        value_query = 'MATCH(n) WHERE id(n) IN [' + ', '.join(str(entry['x_0']) for entry in cursor) + '] RETURN n.value as value'
        cursor = GraphDatabaseUtils.execute_query(value_query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert sorted([entry['value'] for entry in cursor]) == [0,1,2]

    # test check in single child table
    selector = GroupSelector('root', meta, MetricOperator('third_child', 'third_child_int', 0, DataType.Integer,
                                                          MetricOperatorType.Larger))
    query = selector.get_cypher_query()
    assert query == (
        'match (x_0:root {name:"root_pk"}) where x_0:Key\n'
        'match (x_0)--(:first_child {name:"first_child_pk"})--(x_1:third_child {name:"third_child_pk"})\n'
        'match (x_1)--(y_0:Attribute {name:"third_child_int"})\n'
        'with x_0,y_0\n'
        'where y_0.value>0\n'
        'return id(x_0) as x_0')
    if dbms_test:
        cursor = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert len(cursor) == 1
        value_query = 'MATCH(n) WHERE id(n) IN [' + ', '.join(
            str(entry['x_0']) for entry in cursor) + '] RETURN n.value as value'
        cursor = GraphDatabaseUtils.execute_query(value_query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert [entry['value'] for entry in cursor] == [0]

    # test multiple children
    group_filter = AndOperator([
        StringOperator('root', 'root_str', 'some', StringOperatorType.Contains),
        MetricOperator('root', 'root_int', 0, DataType.Integer, MetricOperatorType.Larger),
        MetricOperator('first_child', 'first_child_decimal', 10, DataType.Decimal, MetricOperatorType.SmallerOrEqual),
        StringOperator('second_child', 'second_child_str', 'good bye', StringOperatorType.Equals),
        MetricOperator('third_child', 'third_child_int', -1000, DataType.Integer, MetricOperatorType.Larger),
        StringOperator('fourth_child', 'fourth_child_str', 'o', StringOperatorType.Contains)
    ])
    selector = GroupSelector('root', meta, group_filter)
    query = selector.get_cypher_query()
    assert query == (
        'match (x_0:root {name:"root_pk"}) where x_0:Key\n'
        'match (x_0)--(y_0:Attribute {name:"root_str"})\n'
        'match (x_0)--(y_1:Attribute {name:"root_int"})\n'
        'match (x_0)--(x_1:first_child {name:"first_child_pk"})\n'
        'match (x_1)--(y_2:Attribute {name:"first_child_decimal"})\n'
        'match (x_0)--(x_2:second_child {name:"second_child_pk"})\n'
        'match (x_2)--(y_3:Attribute {name:"second_child_str"})\n'
        'match (x_1)--(x_3:third_child {name:"third_child_pk"})\n'
        'match (x_3)--(y_4:Attribute {name:"third_child_int"})\n'
        'match (x_1)--(x_4:fourth_child {name:"fourth_child_pk"})\n'
        'match (x_4)--(y_5:Attribute {name:"fourth_child_str"})\n'
        'with x_0,y_0,y_1,y_2,y_3,y_4,y_5\n'
        'where (y_0.value contains "some") and (y_1.value>0) and (y_2.value<=10) and '
        '(y_3.value="good bye") and (y_4.value>-1000) and (y_5.value contains "o")\n'
        'return id(x_0) as x_0')
    if dbms_test:
        cursor = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert len(cursor) == 2
        value_query = 'MATCH(n) WHERE id(n) IN [' + ', '.join(
            str(entry['x_0']) for entry in cursor) + '] RETURN n.value as value'
        cursor = GraphDatabaseUtils.execute_query(value_query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert sorted([entry['value'] for entry in cursor]) == [0, 1]

    # test aggregation
    selector = GroupSelector('first_child', meta, AggregatorOperator('root', 'root_str', 2, DataType.String,
                                                                     AggregatorType.Count, MetricOperatorType.Equals))
    query = selector.get_cypher_query()
    assert query == (
        'match (x_0:first_child {name:"first_child_pk"}) where x_0:Key\n'
        'match (x_0)--(x_1:root {name:"root_pk"})\n'
        'optional match (x_1)--(y_0:Attribute {name:"root_str"})\n'
        'with x_0,count(y_0.value) as z_0\n'
        'where z_0=2\n'
        'return id(x_0) as x_0')
    if dbms_test:
        cursor = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert len(cursor) == 1
        value_query = 'MATCH(n) WHERE id(n) IN [' + ', '.join(
            str(entry['x_0']) for entry in cursor) + '] RETURN n.value as value'
        cursor = GraphDatabaseUtils.execute_query(value_query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert [entry['value'] for entry in cursor] == [1]

    # combine single value and aggregation
    group_filter = AndOperator([
        AggregatorOperator('root', 'root_int', 100, DataType.Integer, AggregatorType.Mean, MetricOperatorType.Smaller),
        AggregatorOperator('root', 'root_str', "some", DataType.String, AggregatorType.Concatenate, StringOperatorType.Contains),
        AggregatorOperator('root', 'root_str', "someWord", DataType.String, AggregatorType.List,
                           StringOperatorType.Contains),
        MetricOperator('first_child', 'first_child_decimal', 10, DataType.Decimal, MetricOperatorType.SmallerOrEqual),
        OrOperator([
        MetricOperator('third_child', 'third_child_int', 0, DataType.Integer, MetricOperatorType.Larger),
        NegatedOperator(StringOperator('fourth_child', 'fourth_child_str', 'n', StringOperatorType.Contains))
        ])
    ])
    selector = GroupSelector('first_child', meta, group_filter)
    query = selector.get_cypher_query()
    assert query == (
        'match (x_0:first_child {name:"first_child_pk"}) where x_0:Key\n'
        'match (x_0)--(y_0:Attribute {name:"first_child_decimal"})\n'
        'match (x_0)--(x_1:third_child {name:"third_child_pk"})\n'
        'match (x_1)--(y_1:Attribute {name:"third_child_int"})\n'
        'match (x_0)--(x_2:fourth_child {name:"fourth_child_pk"})\n'
        'match (x_2)--(y_2:Attribute {name:"fourth_child_str"})\n'
        'match (x_0)--(x_3:root {name:"root_pk"})\n'
        'match (x_3)--(y_3:Attribute {name:"root_int"})\n'
        'optional match (x_3)--(y_4:Attribute {name:"root_str"})\n'
        'with x_0,y_0,y_1,y_2,avg(y_3.value) as z_0,apoc.text.join(collect(toString(y_4.value)), ";") as z_1,'
        'collect(distinct y_4.value) as z_2\n'
        'where (z_0<100) and (z_1 contains "some") and ("someWord" in z_2) and (y_0.value<=10) and '
        '((y_1.value>0) or (not (y_2.value contains "n")))\n'
        'return id(x_0) as x_0')
    if dbms_test:
        cursor = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert len(cursor) == 1
        value_query = 'MATCH(n) WHERE id(n) IN [' + ', '.join(
            str(entry['x_0']) for entry in cursor) + '] RETURN n.value as value'
        cursor = GraphDatabaseUtils.execute_query(value_query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert [entry['value'] for entry in cursor] == [0]

    # test all primary keys
    selector = GroupSelector('root', meta, AlwaysTrueOperator())
    query = selector.get_cypher_query()
    assert query == 'match (x_0:root {name:"root_pk"}) where x_0:Key\nwith x_0\nreturn id(x_0) as x_0'
    if dbms_test:
        cursor = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert len(cursor) == 3
        value_query = 'MATCH(n) WHERE id(n) IN [' + ', '.join(
            str(entry['x_0']) for entry in cursor) + '] RETURN n.value as value'
        cursor = GraphDatabaseUtils.execute_query(value_query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert sorted([entry['value'] for entry in cursor]) == [0, 1, 2]

    # test primary key conditions
    selector = GroupSelector('root', meta, AndOperator([
        MetricOperator('root', 'root_pk', 0, DataType.Integer, MetricOperatorType.Equals),
        MetricOperator('first_child', 'first_child_pk', 0, DataType.Integer, MetricOperatorType.Equals)]))
    query = selector.get_cypher_query()
    assert query == ('match (x_0:root {name:"root_pk"}) where x_0:Key\n'
                     'match (x_0)--(x_1:first_child {name:"first_child_pk"})\n'
                     'with x_0,x_1\n'
                     'where (x_0.value=0) and (x_1.value=0)\n'
                     'return id(x_0) as x_0')
    if dbms_test:
        cursor = GraphDatabaseUtils.execute_query(query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert len(cursor) == 1
        value_query = 'MATCH(n) WHERE id(n) IN [' + ', '.join(
            str(entry['x_0']) for entry in cursor) + '] RETURN n.value as value'
        cursor = GraphDatabaseUtils.execute_query(value_query, 'test', address=neo4j_address, auth=neo4j_auth)
        assert sorted([entry['value'] for entry in cursor]) == [0]

def test_exception_handling():
    csv_dir = os.path.join(ROOT_DIR, 'test', 'GraphDataScience', 'test_data', 'group_selector')
    meta_gen = MetaDataGenerator(csv_dir)
    meta = meta_gen.gather_meta_data()
    with pytest.raises(AttributeError) as exc:
        GroupSelector('invalid', meta)
    assert str(exc.value) == 'Group table "invalid" not found in metadata'

    with pytest.raises(AttributeError) as exc:
        GroupSelector('root', meta, MetricOperator('third_child', 'third_child_int', 0, DataType.Decimal,
                                                   MetricOperatorType.Larger))
    assert str(exc.value) == ('Filter data type "Decimal" does not match data type of variable "third_child_int" for '
                              '"third_child" in metadata')

    with pytest.raises(AttributeError) as exc:
        GroupSelector('first_child', meta, MetricOperator('root', 'root_int', 0, DataType.Integer,
                                                          MetricOperatorType.Larger))
    assert str(exc.value) == 'group table "first_child" has no foreign table chain to filter table "root"'

    with pytest.raises(AttributeError) as exc:
        GroupSelector('first_child', meta, AggregatorOperator('third_child', 'third_child_int', 0, DataType.Integer,
                                                              AggregatorType.Count, MetricOperatorType.Larger))
    assert str(exc.value) == ('Filter table "third_child" is marked for aggregation, but has no foreign '
                               'table chain to group table "first_child"')
