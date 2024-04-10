import pytest
import warnings
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.Basis import GraphDatabaseWriter, GraphDatabaseUtils
from graphxplore.Basis.BaseGraph import BaseGraph, BaseNode, BaseEdge, BaseNodeType, BaseLabels, BaseEdgeType
from graphxplore.DataMapping.Conditionals import StringOperator, StringOperatorType
from graphxplore.GraphDataScience import GroupSelector
from graphxplore.Dashboard import DashboardBuilder
from graphxplore.MetaDataHandling import DataType, VariableType, MetaData

meta = MetaData(['root', 'first_child', 'second_child', 'child_child'])
for table in meta.get_table_names():
    var_info = meta.add_variable(table, table + '_pk')
    var_info.data_type = DataType.Integer
    meta.assign_primary_key(table, table + '_pk')
for table in ['first_child', 'second_child']:
    var_info = meta.add_variable('root', table + '_pk')
    var_info.data_type = DataType.Integer
    meta.add_foreign_key('root', table, table + '_pk')
var_info = meta.add_variable('first_child', 'child_child_pk')
var_info.data_type = DataType.Integer
meta.add_foreign_key('first_child', 'child_child', 'child_child_pk')
meta.add_variable('root', 'root_str')
var_info = meta.add_variable('first_child', 'first_child_int')
var_info.data_type = DataType.Integer
var_info.variable_type = VariableType.Metric
var_info = meta.add_variable('second_child', 'second_child_decimal')
var_info.data_type = DataType.Decimal
var_info.variable_type = VariableType.Metric
var_info = meta.add_variable('child_child', 'child_child_int')
var_info.data_type = DataType.Integer
var_info.variable_type = VariableType.Categorical

def test_init_exceptions():
    with pytest.raises(AttributeError) as exc:
        DashboardBuilder(meta=meta, main_table='invalid', base_graph_database='invalid_db')
    assert str(exc.value) == 'Main table "invalid" of dashboard not in specified metadata'
    with pytest.raises(AttributeError) as exc:
        DashboardBuilder(meta=meta, main_table='root', base_graph_database='invalid_db', full_table_group=False)
    assert str(exc.value) == ('You have to either specify at least one group, or set the flag '
                              '"full_table_group" so at least one group will be present')
    groups = {
        'invalid' : GroupSelector(group_table='invalid', meta=MetaData(['invalid']))
    }
    with pytest.raises(AttributeError) as exc:
        DashboardBuilder(meta=meta, main_table='root', base_graph_database='invalid_db', groups=groups)
    assert str(exc.value) == 'Group table of group "invalid" does not match main table of dashboard builder'


def test_queries(neo4j_config):
    run_db_test, neo4j_address, neo4j_auth = neo4j_config
    if not run_db_test:
        warnings.warn('DashboardBuilder database query tests are not executed. If you want to execute them, '
                      'set the flag "--run_neo4j_tests" when running pytest to "True"')
    else:
        try:
            GraphDatabaseUtils.test_connection(neo4j_address, neo4j_auth)
        except AttributeError:
            pytest.fail(
                'Neo4J DBMS for testing not available under given configuration. Adjust parameters "--neo4j_host",'
                ' "--neo4j_port", "--neo4j_user" and/or "--neo4j_pwd"')

        db_name = 'test'
        graph = BaseGraph(nodes=[
            BaseNode(0, BaseLabels(('root',), BaseNodeType.Key), 'root_pk', 0),
            BaseNode(1, BaseLabels(('root',), BaseNodeType.Key), 'root_pk', 1),
            BaseNode(2, BaseLabels(('root',), BaseNodeType.Attribute), 'root_str', 'first'),
            BaseNode(3, BaseLabels(('root',), BaseNodeType.Attribute), 'root_str', 'second'),
            BaseNode(4, BaseLabels(('first_child',), BaseNodeType.Key), 'first_child_pk', 0),
            BaseNode(5, BaseLabels(('first_child',), BaseNodeType.Attribute), 'first_child_int', 13),
            BaseNode(6, BaseLabels(('second_child',), BaseNodeType.Key), 'second_child_pk', 0),
            BaseNode(7, BaseLabels(('second_child',), BaseNodeType.Attribute), 'second_child_decimal', 7.5),
            BaseNode(8, BaseLabels(('child_child',), BaseNodeType.Key), 'child_child_pk', 0),
            BaseNode(9, BaseLabels(('child_child',), BaseNodeType.Attribute), 'child_child_int', 42),
        ],
        edges=[
            BaseEdge(0, 2, BaseEdgeType.HAS_ATTR_VAL),
            BaseEdge(1, 3, BaseEdgeType.HAS_ATTR_VAL),
            BaseEdge(4, 0, BaseEdgeType.CONNECTED_TO),
            BaseEdge(4, 1, BaseEdgeType.CONNECTED_TO),
            BaseEdge(4, 5, BaseEdgeType.HAS_ATTR_VAL),
            BaseEdge(6, 0, BaseEdgeType.CONNECTED_TO),
            BaseEdge(6, 1, BaseEdgeType.CONNECTED_TO),
            BaseEdge(6, 7, BaseEdgeType.HAS_ATTR_VAL),
            BaseEdge(8, 4, BaseEdgeType.CONNECTED_TO),
            BaseEdge(8, 9, BaseEdgeType.HAS_ATTR_VAL),
        ])

        GraphDatabaseWriter.write_graph(
            db_name, graph, overwrite=True, address=neo4j_address, auth=neo4j_auth)

        root_var_info = meta.get_variable('root', 'root_str')
        first_child_var_info = meta.get_variable('first_child', 'first_child_int')
        second_child_var_info = meta.get_variable('second_child', 'second_child_decimal')
        child_child_var_info = meta.get_variable('child_child', 'child_child_int')

        builder = DashboardBuilder(meta, 'root', db_name, address=neo4j_address, auth=neo4j_auth)

        query = builder._get_cypher_query(root_var_info)
        assert query == ('match (x_0:root)--(y:root {name:"root_str"}) where x_0:Key return y.value as '
                         'val, id(x_0) as member_id')

        query = builder._get_cypher_query(child_child_var_info)
        assert query == ('match (x_0:root)--(x_1:first_child)--(x_2:child_child)--'
                         '(y:child_child {name:"child_child_int"}) where x_0:Key '
                         'return y.value as val, id(x_0) as member_id')
        query = builder._get_cypher_query((second_child_var_info, child_child_var_info))
        assert query == ('match (x_0:root)--(x_1:second_child)--(y_0:second_child {name:"second_child_decimal"}) '
                         'where x_0:Key  match (x_0)--(z_1:first_child)--(z_2:child_child)--'
                         '(y_1:child_child {name:"child_child_int"}) return y_0.value as first_val, y_1.value as '
                         'second_val, id(x_0) as member_id')
        query = builder._get_cypher_query((first_child_var_info, child_child_var_info))
        assert query == ('match (x_0:root)--(x_1:first_child)--(y_0:first_child {name:"first_child_int"}) '
                         'where x_0:Key  match (x_1)--(z_2:child_child)--'
                         '(y_1:child_child {name:"child_child_int"}) return y_0.value as first_val, y_1.value as '
                         'second_val, id(x_0) as member_id')

        builder = DashboardBuilder(meta, 'first_child', db_name, address=neo4j_address, auth=neo4j_auth)
        with pytest.raises(AttributeError) as exc:
            builder._get_cypher_query(second_child_var_info)
        assert str(exc.value) == 'No path exists from start table "first_child" to table "second_child" in lattice'

        with pytest.raises(AttributeError) as exc:
            builder.get_variable_dist_plot('root', 'root_str')
        assert str(exc.value) == ('"root" is not a foreign table (or foreign table of foreign table...) of '
                                  '"first_child"')

        with pytest.raises(AttributeError) as exc:
            builder.get_variable_dist_plot('first_child', 'first_child_pk')
        assert str(exc.value) == 'Can only plot distribution for metric and categorical variables'

        with pytest.raises(AttributeError) as exc:
            builder.get_variable_dist_plot('first_child', 'child_child_pk')
        assert str(exc.value) == 'Can only plot distribution for metric and categorical variables'

        groups = {
            'first_group' : GroupSelector('root', meta, StringOperator(
                'root', 'root_str', 'first', StringOperatorType.Equals))
        }
        builder = DashboardBuilder(
            meta, 'root', db_name, groups=groups, address=neo4j_address, auth=neo4j_auth)

        data = builder._query_and_transform_dist_data(root_var_info)
        assert data == {
            'All of table "root"' : {'first' : 1, 'second' : 1},
            'first_group' : {'first' : 1}}

        data = builder._query_and_transform_dist_data(child_child_var_info)
        assert data == {
            'All of table "root"': {42 : 2},
            'first_group': {42: 1}}

        data = builder._query_and_transform_dist_data(first_child_var_info)
        assert data == {
            'first_child_int' : [13, 13, 13],
            'group' : ['All of table "root" (2)', 'first_group (1)', 'All of table "root" (2)']}

        data = builder._query_and_transform_dist_data((root_var_info, child_child_var_info))
        assert data == {
            42: {'All of table "root"': {'first': 1, 'second': 1},
                 'first_group': {'first': 1, 'second': 0}}}

        data = builder._query_and_transform_dist_data((child_child_var_info, root_var_info))
        assert data == {
            'first': {'All of table "root"': {42: 1}, 'first_group': {42: 1}},
            'second': {'All of table "root"': {42: 1}, 'first_group': {42: 0}}}

        data = builder._query_and_transform_dist_data((child_child_var_info, second_child_var_info))
        assert data == {
            'child_child_int': [42, 42, 42],
            'group': ['All of table "root" (2)',
                      'first_group (1)',
                      'All of table "root" (2)'],
            'second_child_decimal': [7.5, 7.5, 7.5]}

        data = builder._query_and_transform_dist_data((second_child_var_info, child_child_var_info))
        assert data == {
            'child_child_int': [42, 42, 42],
            'group': ['All of table "root" (2)',
                      'first_group (1)',
                      'All of table "root" (2)'],
            'second_child_decimal': [7.5, 7.5, 7.5]}

        data = builder._query_and_transform_dist_data((second_child_var_info, first_child_var_info))
        assert data == {
            'first_child_int': [13, 13, 13],
            'group': ['All of table "root" (2)',
                      'first_group (1)',
                      'All of table "root" (2)'],
            'second_child_decimal': [7.5, 7.5, 7.5]}

        data = builder._query_and_transform_dist_data((first_child_var_info, second_child_var_info))
        assert data == {
            'first_child_int': [13, 13, 13],
            'group': ['All of table "root" (2)',
                      'first_group (1)',
                      'All of table "root" (2)'],
            'second_child_decimal': [7.5, 7.5, 7.5]}