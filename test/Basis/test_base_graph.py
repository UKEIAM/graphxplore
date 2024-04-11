import pytest
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.Basis.BaseGraph import BaseNode, BaseEdge, BaseLabels, BaseNodeType, BaseEdgeType, NodeDataType


def test_base_labels():
    invalid_input = 'invalid'
    with pytest.raises(AttributeError) as exc:
        BaseLabels.from_label_string(invalid_input)
    assert str(exc.value) == ('Label string "invalid" is invalid, it should contain at least one label for the '
                              'table or other affiliation and the node type as the last element')

    invalid_input = 'first_label;second_label'
    with pytest.raises(AttributeError) as exc:
        BaseLabels.from_label_string(invalid_input)
    assert str(exc.value) == ('The last entry of the label string "first_label;second_label" must describe '
                              'the node type with one of: "Key", "Attribute", "AttributeBin"')
    valid_input = "MyTable;Attribute"
    labels = BaseLabels.from_label_string(valid_input)
    assert labels.node_type == BaseNodeType.Attribute
    assert labels.membership_labels == ('MyTable',)
    assert labels.to_label_string() == valid_input

def test_nodes():
    invalid_row = {'invalid_key' : 'invalid_val'}
    with pytest.raises(AttributeError) as exc:
        BaseNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain a key "value", "value:long", or "value:double"'
    invalid_row = {'value:long': 'val'}
    with pytest.raises(AttributeError) as exc:
        BaseNode.from_csv_row(invalid_row)
    assert str(exc.value) == '"val" is not of type integer'
    invalid_row = {'value': 'val'}
    with pytest.raises(AttributeError) as exc:
        BaseNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain the field ":ID"'
    valid_row = {
        ':ID' : '0',
        ':LABEL' : 'MyLabel;Attribute',
        'name' : 'attr',
        'value:long' : '42',
        'description' : 'desc'
    }
    node = BaseNode.from_csv_row(valid_row)
    assert node.data_type == NodeDataType.Integer
    assert BaseNode.get_csv_header(NodeDataType.Decimal) == [':ID', ':LABEL', 'name', 'value:double', 'description']
    neo4j_labels, neo4j_params = node.data_for_cypher_write_query()
    assert neo4j_labels == ['MyLabel', 'Attribute']
    assert neo4j_params == {'name' : 'attr', 'value' : 42, 'description' : 'desc'}
    valid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;AttributeBin',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc',
        'refRange:double[]' : '0;100'
    }

    node = BaseNode.from_csv_row(valid_row)
    assert node.bin_info.ref_lower == 0
    assert node.bin_info.ref_upper == 100
    assert BaseNode.get_csv_header(NodeDataType.Bin) == [':ID', ':LABEL', 'name', 'value', 'description', 'refRange:double[]']
    actual = node.to_csv_row()
    assert actual == [0, 'MyLabel;AttributeBin', 'attr', 42, 'desc', '0.0;100.0']
    neo4j_labels, neo4j_params = node.data_for_cypher_write_query()
    assert neo4j_labels == ['MyLabel', 'AttributeBin']
    assert neo4j_params == {'name': 'attr', 'value': 42, 'description': 'desc', 'refRange' : [0, 100]}

def test_edges():
    invalid_row = {'invalid_key': 'invalid_val'}
    with pytest.raises(AttributeError) as exc:
        BaseEdge.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain the field ":START_ID"'
    invalid_row = {':START_ID' : 'val', ':END_ID' : '1', ':TYPE' : 'type'}
    with pytest.raises(AttributeError) as exc:
        BaseEdge.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row entry for field ":START_ID" must be of type int'
    invalid_row = {':START_ID': '0', ':END_ID': '1', ':TYPE': 'invalid'}
    with pytest.raises(AttributeError) as exc:
        BaseEdge.from_csv_row(invalid_row)
    assert str(exc.value) == ('Type "invalid" of BaseEdge not recognized, should be one of "UNASSIGNED", '
                              '"HAS_ATTR_VAL", "CONNECTED_TO", "ASSIGNED_BIN"')
    valid_row = {':START_ID' : '0', ':END_ID' : '1', ':TYPE' : 'HAS_ATTR_VAL'}
    edge = BaseEdge.from_csv_row(valid_row)
    assert edge.source == 0
    assert edge.target == 1
    assert edge.edge_type == BaseEdgeType.HAS_ATTR_VAL
    assert BaseEdge.get_csv_header() == [':START_ID', ':END_ID', ':TYPE']
    actual = edge.to_csv_row()
    assert actual == [0, 1, 'HAS_ATTR_VAL']
    neo4j_edge_type, neo4j_params = edge.data_for_cypher_write_query()
    assert neo4j_edge_type == 'HAS_ATTR_VAL'
    assert neo4j_params == {}

if __name__ == '__main__':
    pytest.main()