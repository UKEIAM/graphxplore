import pytest
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.Basis.BaseGraph import BaseNodeType
from graphxplore.Basis.AttributeAssociationGraph import (AttributeAssociationGraph, AttributeAssociationNode,
                                                         AttributeAssociationEdge, AttributeAssociationEdgeType,
                                                         AttributeAssociationLabels)
from graphxplore.GraphDataScience import (AttributeAssociationGraphPreFilter, AttributeFilter, StringFilterType,
                                          NumericFilterType, CompositionGraphPostFilter, ThresholdGraphPostFilter,
                                          ThresholdParamFilter, GroupFilterMode, OrThresholdFilterCascade,
                                          AndThresholdFilterCascade)

def test_pre_filter_query():
    table_targets = ['first_target', 'second_target']
    table_whitelist = ['first_white', 'second_white']
    table_blacklist = ['first_black', 'second_black']
    name_filters = [
        AttributeFilter('first_name_hint', StringFilterType.Contains, True),
        AttributeFilter('second_name_hint', StringFilterType.Contains, True),
        AttributeFilter('first_name_forbidden', StringFilterType.Contains, False),
        AttributeFilter('second_name_forbidden', StringFilterType.Contains, False)
    ]
    value_filters = [
        AttributeFilter('first_value_string_hint', StringFilterType.Contains, True),
        AttributeFilter('second_value_string_hint', StringFilterType.Contains, True),
        AttributeFilter('value_string_exact', StringFilterType.Equals, True),
        AttributeFilter('value_string_exact_unequal', StringFilterType.UnequalTo, True),
        AttributeFilter('first_value_string_hint_forbidden', StringFilterType.Contains, False),
        AttributeFilter('second_value_string_hint_forbidden', StringFilterType.Contains, False),
        AttributeFilter('value_string_exact_forbidden', StringFilterType.Contains, False),
        AttributeFilter(42, NumericFilterType.Equals, True),
        AttributeFilter(-3.0, NumericFilterType.LargerOrEqual, True),
        AttributeFilter(-5, NumericFilterType.Smaller, False)
    ]
    pre_filter = AttributeAssociationGraphPreFilter(max_path_length=5, whitelist_tables=table_whitelist,
                                                    blacklist_tables=table_blacklist,
                                                    target_tables=table_targets, name_filters=name_filters,
                                                    value_filters=value_filters)
    actual_query = pre_filter.get_query(1)
    expected_query = ('match (r) where id(r) = 1 call apoc.path.expandConfig(r, '
                      '{relationshipFilter: "HAS_ATTR_VAL>|<CONNECTED_TO|ASSIGNED_BIN>" , minLevel: '
                      '1, uniqueness: "NODE_GLOBAL", maxLevel: 5, labelFilter: '
                      '"/first_target|/second_target|+first_white|+second_white|-first_black|-second_black"}) '
                      'yield path with last(nodes(path)) as n match (n) where not '
                      'exists{(n)-[:ASSIGNED_BIN]->(:AttributeBin)} '
                      'and (n.name contains "first_name_hint" or n.name contains "second_name_hint") '
                      'and not (n.name contains "first_name_forbidden" or n.name contains "second_name_forbidden") '
                      'and (not apoc.meta.isType(n.value, "STRING") '
                      'or ((n.value contains "first_value_string_hint" or n.value contains "second_value_string_hint" '
                      'or n.value = "value_string_exact" or n.value <> "value_string_exact_unequal") '
                      'and not (n.value contains "first_value_string_hint_forbidden" '
                      'or n.value contains "second_value_string_hint_forbidden" '
                      'or n.value contains "value_string_exact_forbidden"))) '
                      'and (apoc.meta.isType(n.value, "STRING") or ((n.value = 42 or n.value >= -3.0) '
                      'and not (n.value < -5))) '
                      'return distinct id(n) as node_id, labels(n) as labels, n.name as name, n.value as '
                      'value, n.description as desc, n.refRange as refRange')
    assert actual_query == expected_query

def test_threshold_post_filtering():
    with pytest.raises(AttributeError) as exc:
        ThresholdParamFilter('invalid')
    assert str(exc.value) == ('Parameter "invalid" not recognized for filtering, available parameters are: '
                              '"count", "missing", "prevalence", "prevalence_difference", '
                              '"prevalence_ratio", "co_occurrence", "conditional_prevalence", '
                              '"conditional_increase", "increase_ratio')
    with pytest.raises(AttributeError) as exc:
        ThresholdParamFilter('count', min_val=-1)
    assert str(exc.value) == ('For the filtering of parameter "count" the smallest possible lower bound is '
                              '0, but -1 was specified')
    with pytest.raises(AttributeError) as exc:
        ThresholdParamFilter('conditional_prevalence', max_val=1.5)
    assert str(exc.value) == ('For the filtering of parameter "conditional_prevalence" the largest possible '
                              'upper bound is 1.0, but 1.5 was specified')
    with pytest.raises(AttributeError) as exc:
        ThresholdParamFilter('conditional_prevalence')
    assert str(exc.value) == ('You have to specify the filter mode, since "conditional_prevalence" is a '
                              'group-dependent parameter')
    labels = AttributeAssociationLabels(('test',), BaseNodeType.Attribute)
    groups = ['group1', 'group2']
    node = AttributeAssociationNode(1, labels, 'first',
                                   'val', groups,
                                   count={'group1' : 1, 'group2' : 2})
    count_filter = ThresholdParamFilter('count', min_val=2, mode=GroupFilterMode.Any)
    assert count_filter.is_valid(node)
    count_filter = ThresholdParamFilter('count', min_val=2, mode=GroupFilterMode.All)
    assert not count_filter.is_valid(node)
    graph = AttributeAssociationGraph(nodes=[
        AttributeAssociationNode(1, labels, 'one', 'val', groups, prevalence={'group1' : 0.7, 'group2' : 0.3},
                                 prevalence_difference=0.4, prevalence_ratio=2.334),
        AttributeAssociationNode(2, labels, 'two', 'val', groups, prevalence={'group1': 0.4, 'group2': 0.1},
                                 prevalence_difference=0.3, prevalence_ratio=4)
    ],
    edges= [
        AttributeAssociationEdge(1, 2, groups, co_occurrence={'group1' : 5, 'group2' : 3})
    ])
    post_filter = ThresholdGraphPostFilter(node_filter=ThresholdParamFilter('prevalence_difference', min_val=0.2))
    filtered = post_filter.filter_graph(graph)
    assert len(filtered.nodes) == 2 and len(filtered.edges) == 1
    post_filter = ThresholdGraphPostFilter(node_filter=ThresholdParamFilter('prevalence_difference', max_val=0.3))
    filtered = post_filter.filter_graph(graph)
    assert len(filtered.nodes) == 1 and len(filtered.edges) == 0
    post_filter = ThresholdGraphPostFilter(edge_filter=ThresholdParamFilter('co_occurrence', max_val=4,
                                                                            mode=GroupFilterMode.All))
    filtered = post_filter.filter_graph(graph)
    assert len(filtered.nodes) == 2 and len(filtered.edges) == 0
    post_filter = ThresholdGraphPostFilter(node_filter=AndThresholdFilterCascade([
        ThresholdParamFilter('prevalence_difference', max_val=0.3),
        ThresholdParamFilter('prevalence_ratio', max_val=3.0)
    ]))
    filtered = post_filter.filter_graph(graph)
    assert len(filtered.nodes) == 0 and len(filtered.edges) == 0
    post_filter = ThresholdGraphPostFilter(node_filter=OrThresholdFilterCascade([
        ThresholdParamFilter('prevalence_difference', max_val=0.3),
        ThresholdParamFilter('prevalence_ratio', max_val=3.0)
    ]))
    filtered = post_filter.filter_graph(graph)
    assert len(filtered.nodes) == 2 and len(filtered.edges) == 1

def test_composition_post_filter():
    with pytest.raises(AttributeError) as exc:
        CompositionGraphPostFilter(min_prevalence=1.5)
    assert str(exc.value) == 'Parameter "min_prevalence" must be at least 0 and at most 1'
    with pytest.raises(AttributeError) as exc:
        CompositionGraphPostFilter(node_comp_ratio=(0.5, 0.3, 0.3))
    assert str(exc.value) == 'Node compositions ratios must sum to one'
    with pytest.raises(AttributeError) as exc:
        CompositionGraphPostFilter(max_nof_edges=-5)
    assert str(exc.value) == 'Parameter "max_nof_edges" must be greater than 0'

    labels = AttributeAssociationLabels(('test',), BaseNodeType.Attribute)
    groups = ['group1', 'group2']
    graph = AttributeAssociationGraph(nodes=[
        AttributeAssociationNode(1, labels, 'no_support', 'val', groups,
                                 missing={'group1': 0.005, 'group2': 0.005},
                                 prevalence={'group1': 0.7, 'group2': 0.3},
                                 prevalence_difference=0.4, prevalence_ratio=2.334),
        AttributeAssociationNode(2, labels, 'specific', 'val', groups,
                                 missing={'group1': 0.4, 'group2': 0.1},
                                 prevalence={'group1': 0.4, 'group2': 0.1},
                                 prevalence_difference=0.3, prevalence_ratio=4),
        AttributeAssociationNode(3, labels, 'sensitive', 'val', groups, missing={'group1': 0.2, 'group2': 0.2},
                                 prevalence={'group1': 0.7, 'group2': 0.3},
                                 prevalence_difference=0.4, prevalence_ratio=2.334),
        AttributeAssociationNode(4, labels, 'frequent', 'val', groups,
                                 missing={'group1': 0.4, 'group2': 0.3},
                                 prevalence={'group1': 0.9, 'group2': 0.8},
                                 prevalence_difference=0.1, prevalence_ratio=1.125)
    ])

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, max_missing=0.2, max_missing_mode=GroupFilterMode.All)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 3]

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, max_missing=0.2, max_missing_mode=GroupFilterMode.Any)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3]


    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, min_prevalence=0.2, max_missing=1.0,
                                             min_prevalence_mode=GroupFilterMode.All)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 3, 4]


    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, min_prevalence=0.2, max_missing=1.0,
                                             min_prevalence_mode=GroupFilterMode.Any)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3, 4]

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=0.75, max_missing=1.0, node_comp_ratio=(0.34, 0.33, 0.33))
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 4]
    post_filter = CompositionGraphPostFilter(perc_nof_nodes=0.75, max_missing=1.0, node_comp_ratio=(0.4, 0.5, 0.1))
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 3, 4]
    post_filter = CompositionGraphPostFilter(perc_nof_nodes=0.75, max_missing=1.0, node_comp_ratio=(0.0, 0.0, 1.0))
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3]

    graph.edges = [
        AttributeAssociationEdge(1, 2, groups, conditional_prevalence={'group1': 0.9, 'group2': 0.9},
                                 conditional_increase={'group1': 0.5, 'group2': 0.8},
                                 increase_ratio={'group1' : 2.25, 'group2' : 9.0}),
        AttributeAssociationEdge(3, 4, groups, conditional_prevalence={'group1': 0.5, 'group2': 0.4},
                                 conditional_increase={'group1': -0.4, 'group2': -0.4},
                                 increase_ratio={'group1': 0.556, 'group2': 0.5})
    ]

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, perc_nof_edges=1.0, max_missing=1.00,
                                            min_cond_prevalence=0.5, min_cond_prevalence_mode=GroupFilterMode.Any)
    filtered = post_filter.filter_graph(graph)
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(1, 2), (3, 4)]
    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, perc_nof_edges=1.0, max_missing=1.00,
                                             min_cond_prevalence=0.5, min_cond_prevalence_mode=GroupFilterMode.All)
    filtered = post_filter.filter_graph(graph)
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(1, 2)]

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, perc_nof_edges=1.0,  max_missing=1.00,
                                             min_cond_prevalence=0.0)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3, 4]
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(1, 2), (3, 4)]
    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, perc_nof_edges=1.0, max_missing=1.00,
                                             min_cond_prevalence=0.55, min_cond_prevalence_mode=GroupFilterMode.All)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3, 4]
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(1, 2)]
    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, perc_nof_edges=1.0, max_missing=1.00,
                                             min_prevalence=0.2, min_cond_prevalence=0.00)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 3, 4]
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(3, 4)]

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, perc_nof_edges=0.9, max_missing=1.00,
                                             min_prevalence=0.2, min_cond_prevalence=0.00)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 3, 4]
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(3, 4)]

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, perc_nof_edges=0.5, max_missing=1.00,
                                             min_prevalence=0.0, min_cond_prevalence=0.00,
                                             edge_comp_ratio=(1.0, 0.0, 0.0))
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3, 4]
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(1, 2)]

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, perc_nof_edges=0.5, min_prevalence=0.00,
                                             max_missing=1.0, min_cond_prevalence=0.00, edge_comp_ratio=(0.4, 0.6, 0.0))
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3, 4]
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(1, 2)]

    # only one group, only high attribute shares are used as filter
    groups = ['group1']
    graph = AttributeAssociationGraph(nodes=[
        AttributeAssociationNode(1, labels, 'no_support', 'val', groups,
                                 missing={'group1': 0.005},
                                 prevalence={'group1': 0.7}),
        AttributeAssociationNode(2, labels, 'specific', 'val', groups, missing={'group1': 0.4},
                                 prevalence={'group1': 0.4}),
        AttributeAssociationNode(3, labels, 'sensitive', 'val', groups, missing={'group1': 0.0},
                                 prevalence={'group1': 0.7}),
        AttributeAssociationNode(4, labels, 'frequent', 'val', groups, missing={'group1': 0.0},
                                 prevalence={'group1': 0.9})
    ])
    post_filter = CompositionGraphPostFilter(perc_nof_nodes=0.75, max_missing=1.0, min_prevalence=0.0,
                                             node_comp_ratio=(0.4, 0.5, 0.1))
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 3, 4]

    # test negative influence filtering
    labels = AttributeAssociationLabels(('test',), BaseNodeType.Attribute)
    groups = ['group1', 'group2']
    graph = AttributeAssociationGraph(nodes=[
        AttributeAssociationNode(1, labels, 'no_support', 'val', groups,
                                 missing={'group1': 0.005, 'group2': 0.005},
                                 prevalence={'group1': 0.7, 'group2': 0.3},
                                 prevalence_difference=0.4, prevalence_ratio=2.334),
        AttributeAssociationNode(2, labels, 'specific', 'val', groups, missing={'group1': 0.0, 'group2': 0.0},
                                 prevalence={'group1': 0.4, 'group2': 0.1},
                                 prevalence_difference=0.3, prevalence_ratio=4),
        AttributeAssociationNode(3, labels, 'sensitive', 'val', groups, missing={'group1': 0.0, 'group2': 0.0},
                                 prevalence={'group1': 0.7, 'group2': 0.3},
                                 prevalence_difference=0.4, prevalence_ratio=2.334),
        AttributeAssociationNode(4, labels, 'frequent', 'val', groups, missing={'group1': 0.0, 'group2': 0.0},
                                 prevalence={'group1': 0.9, 'group2': 0.8},
                                 prevalence_difference=0.1, prevalence_ratio=1.125)
    ], edges=[
        AttributeAssociationEdge(1, 2, groups, conditional_prevalence={'group1': 0.9, 'group2': 0.9},
                                 conditional_increase={'group1': 0.5, 'group2': 0.8},
                                 increase_ratio={'group1': 2.25, 'group2': 9.0}),
        AttributeAssociationEdge(3, 4, groups, conditional_prevalence={'group1': 0.0, 'group2': 0.4},
                                 conditional_increase={'group1': -0.9, 'group2': -0.4},
                                 increase_ratio={'group1': 0.0, 'group2': 0.5})
    ])

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, max_missing=1.00, min_prevalence=0.0,
                                             min_cond_prevalence=0.0, perc_nof_edges=0.5,
                                             include_conditional_decrease=False)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3, 4]
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(1, 2)]

    post_filter = CompositionGraphPostFilter(perc_nof_nodes=1.0, max_missing=1.00, min_prevalence=0.0,
                                             min_cond_prevalence=0.0, perc_nof_edges=0.5,
                                             include_conditional_decrease=True)
    filtered = post_filter.filter_graph(graph)
    assert sorted([node.node_id for node in filtered.nodes]) == [1, 2, 3, 4]
    assert sorted([(edge.source, edge.target) for edge in filtered.edges]) == [(3, 4)]


