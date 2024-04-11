import pytest
import math
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.Basis.BaseGraph import BaseNodeType, BinBoundInfo
from graphxplore.Basis.AttributeAssociationGraph import *

def test_label():
    label_str = 'MyLabel;HighlyRelated;Infrequent;OtherLabel;AttributeBin'
    labels = AttributeAssociationLabels.from_label_string(label_str)
    assert labels.node_type == BaseNodeType.AttributeBin
    assert labels.membership_labels == ('MyLabel', 'OtherLabel')
    assert labels.distinction_label == DistinctionLabel.HighlyRelated
    assert labels.frequency_label == FrequencyLabel.Infrequent
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationLabels.from_label_list(['invalid'])
    assert str(exc.value) == ('The label string should contain at least one label for the table or other affiliation '
                              'and the node type as the last element')

def test_nodes():
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode(0, AttributeAssociationLabels(('table', ), BaseNodeType.Attribute), 'name', 'val', groups=[])
    assert str(exc.value) == 'You have to define at least one group'
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode(0, AttributeAssociationLabels(('table', ), BaseNodeType.Attribute), 'name', 'val',
                                 groups=['this', 'other'], positive_group='this', negative_group='this')
    assert str(exc.value) == 'Positive and negative group cannot be identical'
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode(0, AttributeAssociationLabels(('table', ), BaseNodeType.Attribute), 'name', 'val',
                                 groups=['this', 'other'], positive_group='this', negative_group='invalid')
    assert str(exc.value) == 'Negative group "invalid" not in list of groups'
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode(0, AttributeAssociationLabels(('table', ), BaseNodeType.Attribute), 'name', 'val',
                                 groups=['this', 'other'], positive_group='this', negative_group=None)
    assert str(exc.value) == 'Either both or none of positive and negative group have be specified'

    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode(0, AttributeAssociationLabels(('table', ), BaseNodeType.Attribute), 'name', 'val',
                                 groups=['this', 'other'], count={'this' : 1})
    assert str(exc.value) == 'Count not specified for group "other"'

    invalid_row = {'invalid_key': 'invalid_val'}
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain a key "value", "value:long", or "value:double"'
    invalid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;Attribute',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc'
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain the field "groups[]"'

    invalid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;Attribute',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc',
        'groups[]': 'group1;group2',
        'count:long[]': 'invalid',
        'missing:double[]' : 'invalid',
        'prevalence:double[]' : 'invalid',
        'prevalence_difference:double' : 'invalid'
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row entry for field "prevalence_difference:double" must be of type float'
    invalid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;Attribute',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc',
        'count:long[]': 'invalid',
        'missing:double[]': 'invalid',
        'prevalence:double[]': 'invalid',
        'prevalence_difference:double': 0.2,
        'prevalence_ratio:double': 1.3
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain the field "groups[]"'
    invalid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;Attribute',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc',
        'groups[]': 'group1;group2',
        'count:long[]': 'invalid',
        'missing:double[]': 'invalid',
        'prevalence:double[]': 'invalid',
        'prevalence_difference:double': 0.2,
        'prevalence_ratio:double': 1.3
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row group substring "group1" is invalid'
    invalid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;Attribute',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc',
        'groups[]': 'group1 (invalid);group2',
        'count:long[]': 'invalid',
        'missing:double[]': 'invalid',
        'prevalence:double[]': 'invalid',
        'prevalence_difference:double': 0.2,
        'prevalence_ratio:double': 1.3
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row group substring "group1 (invalid)" has invalid group size specifier'
    invalid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;Attribute',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc',
        'groups[]': 'group1 (2)[+];group2 (14)[+]',
        'count:long[]': 'invalid',
        'missing:double[]': 'invalid',
        'prevalence:double[]': 'invalid',
        'prevalence_difference:double': 0.2,
        'prevalence_ratio:double': 1.3
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode.from_csv_row(invalid_row)
    assert str(exc.value) == ('Two groups "group1" and "group2" are specified as positive in group string '
                              'list "group1 (2)[+]", "group2 (14)[+]"')
    invalid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;Attribute',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc',
        'groups[]': 'group1 (2)[+];group2 (14)[-]',
        'count:long[]' : 'invalid;alsoInvalid',
        'missing:double[]': 'invalid',
        'prevalence:double[]': 'invalid',
        'prevalence_difference:double': 0.2,
        'prevalence_ratio:double': 1.3
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationNode.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain integers seperated by semicolons in field "count:long[]"'
    valid_row = {
        ':ID': '0',
        ':LABEL': 'MyLabel;Attribute;Related;Frequent',
        'name': 'attr',
        'value:long': '42',
        'description': 'desc',
        'groups[]': 'group1 (2)[+];group2 (14)[-]',
        'count:long[]' : '1;2',
        'missing:double[]' : '0.1;0.05',
        'prevalence:double[]' : '0.6;0.16',
        'prevalence_difference:double': 0.2,
        'prevalence_ratio:double': 1.3
    }
    node = AttributeAssociationNode.from_csv_row(valid_row)
    assert AttributeAssociationNode.get_csv_header(node.data_type) == [
        ':ID',
        ':LABEL',
        'name',
        'value:long',
        'description',
        'groups[]',
        'count:long[]',
        'missing:double[]',
        'prevalence:double[]',
        'prevalence_difference:double',
        'prevalence_ratio:double'
    ]

    assert node.labels.distinction_label == DistinctionLabel.Related
    assert node.prevalence['group1'] == 0.6
    assert node.prevalence_ratio == 1.3
    assert node.to_csv_row() == [
        0,
        'MyLabel;Attribute;Related;Frequent',
        'attr',
        42,
        'desc',
        'group1 (2)[+];group2 (14)[-]',
        '1;2',
        '0.1;0.05',
        '0.6;0.16',
        0.2,
        1.3]
    neo4j_labels, neo4j_params = node.data_for_cypher_write_query()
    assert neo4j_labels == ['MyLabel', 'Attribute', 'Related', 'Frequent']
    assert neo4j_params == {'name' : 'attr', 'value' : 42, 'description' : 'desc',
                            'groups' : ['group1 (2)[+]', 'group2 (14)[-]'], 'count' : [1, 2], 'missing' : [0.1, 0.05],
                            'prevalence' : [0.6, 0.16], 'prevalence_difference' : 0.2, 'prevalence_ratio' : 1.3}

    node = AttributeAssociationNode(
        node_id=0,
        labels=AttributeAssociationLabels(('MyTable',), BaseNodeType.AttributeBin, FrequencyLabel.Infrequent,
                                          DistinctionLabel.Related),
        name='attr_bin', val='low',  groups=['group1', 'group2'], desc='desc', bin_info=BinBoundInfo(-1.0, 1.0),
        positive_group='group1', negative_group='group2', group_size={'group1': 2, 'group2': 14},
        count={'group1' : 1, 'group2' : 0}, missing={'group1' : 0.1, 'group2' : 0.8},
        prevalence={'group1' : 0.2, 'group2' : 0.0}, prevalence_difference=0.2, prevalence_ratio=math.inf)

    assert node.to_csv_row() == [0,
                                 'MyTable;AttributeBin;Related;Infrequent',
                                 'attr_bin',
                                 'low',
                                 'desc',
                                 '-1.0;1.0',
                                 'group1 (2)[+];group2 (14)[-]',
                                 '1;0',
                                 '0.1;0.8',
                                 '0.2;0.0',
                                 0.2,
                                 math.inf]

    neo4j_labels, neo4j_params = node.data_for_cypher_write_query()
    assert neo4j_labels == ['MyTable', 'AttributeBin', 'Related', 'Infrequent']
    assert neo4j_params == {'name': 'attr_bin', 'value': 'low', 'description': 'desc', 'refRange' : [-1.0, 1.0],
                            'groups': ['group1 (2)[+]', 'group2 (14)[-]'], 'count': [1, 0],
                            'missing': [0.1, 0.8], 'prevalence': [0.2, 0.0], 'prevalence_difference': 0.2,
                            'prevalence_ratio': math.inf}

def test_edges():
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationEdge(0, 1, groups=[])
    assert str(exc.value) == 'You have to define at least one group'
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationEdge(0, 1, groups=['this'], co_occurrence={'other' : 0})
    assert str(exc.value) == 'Co-occurrence count not specified for group "this"'
    invalid_row = {
        ':START_ID': '0', ':END_ID': '1', ':TYPE': 'HAS_ATTR_VAL', 'groups[]' : 'invalid',
        'co_occurrence:long[]' : 'invalid', 'conditional_prevalence:double[]': 'invalid',
        'conditional_increase:double[]' : 'invalid',
        'increase_ratio:double[]' : 'invalid',}
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationEdge.from_csv_row(invalid_row)
    assert str(exc.value) == ('Type "HAS_ATTR_VAL" of AttributeAssociationEdge not recognized, should be '
                              'one of "UNASSIGNED", "LOW_RELATION", "MEDIUM_RELATION", "HIGH_RELATION"')

    invalid_row = {':START_ID': '0', ':END_ID': '1', ':TYPE': 'LOW_RELATION'}
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationEdge.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain the field "groups[]"'
    invalid_row = {
        ':START_ID': '0',
        ':END_ID': '1',
        ':TYPE': 'LOW_RELATION',
        'groups[]': 'group1 (2)[+];group2 (14)[-]',
        'co_occurrence:long[]': '42;1337'
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationEdge.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain the field "conditional_prevalence:double[]"'
    invalid_row = {
        ':START_ID': '0',
        ':END_ID': '1',
        ':TYPE': 'LOW_RELATION',
        'groups[]': 'group1 (2)[+];group2 (14)[-]',
        'co_occurrence:long[]': '42;1337',
        'conditional_prevalence:double[]': '0.2',
        'conditional_increase:double[]' : '0.1;0.0',
        'increase_ratio:double[]' : '1.5;1.0',
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationEdge.from_csv_row(invalid_row)
    assert str(exc.value) == 'Conditional prevalence not specified for group "group2"'
    invalid_row = {
        ':START_ID': '0',
        ':END_ID': '1',
        ':TYPE': 'LOW_RELATION',
        'groups[]': 'group1 (2)[+];group2 (14)[-]',
        'co_occurrence:long[]': '42;1337',
        'conditional_prevalence:double[]': '0.2;invalid',
        'conditional_increase:double[]' : '0.1;0.0',
        'increase_ratio:double[]' : '1.5;1.0'
    }
    with pytest.raises(AttributeError) as exc:
        AttributeAssociationEdge.from_csv_row(invalid_row)
    assert str(exc.value) == 'CSV row must contain floats seperated by semicolons in field "conditional_prevalence:double[]"'

    valid_row = {
        ':START_ID': '0',
        ':END_ID': '1',
        ':TYPE': 'LOW_RELATION',
        'groups[]': 'group1 (2)[+];group2 (14)[-]',
        'co_occurrence:long[]': '42;1337',
        'conditional_prevalence:double[]': '0.2;0.5',
        'conditional_increase:double[]' : '0.1;0.0',
        'increase_ratio:double[]' : '1.5;1.0'
    }
    edge = AttributeAssociationEdge.from_csv_row(valid_row)
    assert edge.source == 0
    assert edge.target == 1
    assert edge.edge_type == AttributeAssociationEdgeType.LOW_RELATION
    assert edge.conditional_prevalence['group2'] == 0.5
    assert AttributeAssociationEdge.get_csv_header() == [
        ':START_ID',
        ':END_ID',
        ':TYPE',
        'groups[]',
        'co_occurrence:long[]',
        'conditional_prevalence:double[]',
        'conditional_increase:double[]',
        'increase_ratio:double[]'
    ]
    assert edge.to_csv_row() == [
        0,
        1,
        'LOW_RELATION',
        'group1 (2)[+];group2 (14)[-]',
        '42;1337',
        '0.2;0.5',
        '0.1;0.0',
        '1.5;1.0'
    ]
    neo4j_edge_type, neo4j_params = edge.data_for_cypher_write_query()
    assert neo4j_edge_type == 'LOW_RELATION'
    assert neo4j_params == {'groups' : ['group1 (2)[+]', 'group2 (14)[-]'], 'co_occurrence' : [42, 1337],
                            'conditional_prevalence' : [0.2, 0.5],
                            'conditional_increase' : [0.1, 0.0], 'increase_ratio' : [1.5, 1.0]}

if __name__ == '__main__':
    pytest.main()