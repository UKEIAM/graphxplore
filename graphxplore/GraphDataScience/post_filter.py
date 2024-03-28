from typing import Optional, Iterable, List, Union, Tuple
from enum import Enum
import math
from graphxplore.Basis.AttributeAssociationGraph import AttributeAssociationGraph, AttributeAssociationNode, AttributeAssociationEdge

class AttributeAssociationGraphPostFilter:
    """This is the abstract parent class of all post filter for attribute association graphs. Post filter assess the
    statistical metrics calculated for attribute and either use thresholds (:class:`ThresholdGraphPostFilter`) or
    select the attributes based on a composition of metric values (:class:`CompositionGraphPostFilter`).
    """
    def filter_graph(self, graph : AttributeAssociationGraph) -> AttributeAssociationGraph:
        """Filters the given graph by its statistical traits

        :param graph: The graph to filter
        :return: Returns the new, filtered graph
        """
        raise NotImplementedError('Never call parent class')

class GroupFilterMode(str, Enum):
    """Specifies if only one or all group metrics must pass the filter criteria.
    """
    Any = 'Any'
    All = 'All'

class ThresholdGraphPostFilter(AttributeAssociationGraphPostFilter):
    """This class filters the nodes and edges of a
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationGraph` based on property thresholds. The
    thresholds can be arbitrarily combined by conjunctions and disjunctions.

    :param node_filter: The filter applied to nodes
    :param edge_filter: The filter applied to edges
    """
    def __init__(self, node_filter : Optional['ThresholdFilter'] = None,
                 edge_filter : Optional['ThresholdFilter'] = None):
        """Constructor method
        """
        self.node_filter = node_filter
        self.edge_filter = edge_filter

    def filter_graph(self, graph : AttributeAssociationGraph) -> AttributeAssociationGraph:
        ids_to_delete = set()
        if self.node_filter is None:
            remaining_nodes = graph.nodes
        else:
            remaining_nodes = []
            for node in graph.nodes:
                if not self.node_filter.is_valid(node):
                    ids_to_delete.add(node.node_id)
                else:
                    remaining_nodes.append(node)
        if len(ids_to_delete) == 0 and self.edge_filter is None:
            remaining_edges = graph.edges
        else:
            remaining_edges = []
            for edge in graph.edges:
                if edge.source in ids_to_delete or edge.target in ids_to_delete:
                    continue
                if self.edge_filter is None or self.edge_filter.is_valid(edge):
                    remaining_edges.append(edge)
        return AttributeAssociationGraph(remaining_nodes, remaining_edges)

class CompositionGraphPostFilter(AttributeAssociationGraphPostFilter):
    """This class filters an attribute association graph based on user-defined score composition ratios. For each score,
    the nodes or edges with the highest values will be selected and the graph will be filled with them according to the
    specified ratio. The node ratio can be built out of the following three metrics:

    - high maximum prevalence: These attributes appear often in the group with the highest prevalence, but are not
      necessarily selective for that specific group
    - high prevalence difference: These attributes appear more often in one group compared another in absolute
      terms. Thus, this attribute has a sensitivity for that group. But they could still have some prevalence in
      another group, meaning their specificity could be low
    - high prevalence ratio: These attributes are specific for one group compared to another group. But all
      prevalence could be low and the sensitivity of the attribute could be low as well as a result.

    The edge ratio can be built out of the following three metrics for a relation A->B:

    - high maximum conditional prevalence: Many members with attribute A, also exhibit attribute B in the group
      with the highest conditional prevalence. However, B could just have a high prevalence itself and thus the
      added condition of A would have little influence
    - high maximum conditional increase: The added condition of A has a high sensitivity for the presence of B in at
      least one group. However, the prevalence B could be high as well, meaning A would not be specific for B
    - high maximum conditional increase: The added condition of A has a high specificity for the presence of B in at
      least one group. However, the conditional prevalence could be low, meaning A would not be sensitive for the
      presence of B

    Additionally, a minimal prevalence and conditional prevalence, as well as maximum missing value ratio can be specified.
    Moreover, the number of nodes and edges in the filtered graph can be adjusted using a percentage of the unfiltered
    amount or an absolute value. If  both the percentage and absolute value are specified, the smallest resulting
    number of nodes or edges will be taken.

    NOTE: Since attribute association graphs with only one group have no prevalence difference and ratio metrics, only
    the nodes with the highest prevalence will be selected

    :param min_prevalence: Nodes with a prevalence below this value will be removed, defaults to 1%
    :param min_prevalence_mode: Specifies if only one or all groups must pass `min_prevalence`, defaults to
        ``GroupFilterMode.All``
    :param min_cond_prevalence: Edges with a conditional prevalence below this value in all groups will be removed,
        defaults to 5%
    :param min_cond_prevalence_mode: Specifies if only one or all groups must pass `min_cond_prevalence`,
        defaults to ``GroupFilterMode.All``
    :param max_missing: Nodes with a missing ratio above this value will be removed, defaults to 20%
    :param max_missing_mode: Specifies if only one or all groups must pass `max_missing`, defaults to
        ``GroupFilterMode.All``
    :param perc_nof_nodes: Percentage of nodes that should remain of all the nodes passing `min_prevalence` and
        `max_missing`, defaults to 50%
    :param perc_nof_edges: Percentage of edges that should remain of all edges passing `min_cond_prevalence`, defaults
        to 25%
    :param node_comp_ratio: The percentage of nodes with high maximal prevalence/difference/ratio after filtering.
        Ratios must sum to 1.0. Defaults to 20%/50%/30%
    :param edge_comp_ratio: The percentage of edges with
        high maximal conditional prevalence/maximal conditional increase/maximal conditional increase ratio after
        filtering. Ratios must sum to 1.0. Defaults to 20%/50%/30%
    :param max_nof_nodes: The maximum number of nodes that should exist in the graph after filtering, defaults to
        ``None`` (meaning no filtering applied with this threshold)
    :param max_nof_edges: The maximum number of edges that should exist in the graph after filtering, defaults to
        ``None``  (meaning no filtering applied with this threshold)
    :param include_conditional_decrease: Specifies, if negative absolute conditional increase and conditional
        increase ratio smaller than 1.0 should be identified as high conditional increase (and ratio) in the edge
        composition. Defaults to ``False``
    """
    def __init__(self, min_prevalence : float = 0.01, min_prevalence_mode : GroupFilterMode = GroupFilterMode.All,
                 min_cond_prevalence : float = 0.05, min_cond_prevalence_mode : GroupFilterMode = GroupFilterMode.All,
                 max_missing : float = 0.20, max_missing_mode : GroupFilterMode = GroupFilterMode.All,
                 perc_nof_nodes : float = 0.5, perc_nof_edges = 0.25,
                 node_comp_ratio : Tuple[float, float, float] = (0.2,0.5,0.3),
                 edge_comp_ratio : Tuple[float, float, float] = (0.2,0.5,0.3),
                 max_nof_nodes : Optional[int] = None, max_nof_edges : Optional[int] = None,
                 include_conditional_decrease : bool = False):
        """Constructor method
        """
        if not 0 <= min_prevalence <= 1:
            raise AttributeError('Parameter "min_prevalence" must be at least 0 and at most 1')
        self.min_prevalence = min_prevalence
        self.min_prevalence_mode = min_prevalence_mode
        if not 0 <= min_cond_prevalence <= 1:
            raise AttributeError('Parameter "min_cond_prevalence" must be at least 0 and at most 1')
        self.min_cond_prevalence = min_cond_prevalence
        self.min_cond_prevalence_mode = min_cond_prevalence_mode
        if not 0 <= max_missing <= 1:
            raise AttributeError('Parameter "max_missing" must be at least 0 and at most 1')
        self.max_missing = max_missing
        self.max_missing_mode = max_missing_mode
        if not 0 <= perc_nof_nodes <= 1:
            raise AttributeError('Parameter "perc_nof_nodes" must be at least 0 and at most 1')
        self.perc_nof_nodes = perc_nof_nodes
        if not 0 <= perc_nof_edges <= 1:
            raise AttributeError('Parameter "perc_nof_edges" must be at least 0 and at most 1')
        self.perc_nof_edges = perc_nof_edges
        if not round(sum(node_comp_ratio), 5) == 1:
            raise AttributeError('Node compositions ratios must sum to one')
        self.node_comp_ratio = node_comp_ratio
        if not round(sum(edge_comp_ratio), 5):
            raise AttributeError('Edge compositions ratios must sum to one')
        self.edge_comp_ratio = edge_comp_ratio
        if max_nof_nodes is not None and max_nof_nodes < 1:
            raise AttributeError('Parameter "max_nof_nodes" must be greater than 0')
        self.max_nof_nodes = max_nof_nodes
        if max_nof_edges is not None and max_nof_edges < 1:
            raise AttributeError('Parameter "max_nof_edges" must be greater than 0')
        self.max_nof_edges = max_nof_edges
        self.include_conditional_decrease = include_conditional_decrease

    def filter_graph(self, graph : AttributeAssociationGraph) -> AttributeAssociationGraph:
        if self.min_prevalence > 0:
            prev_filter_func = max if self.min_prevalence_mode == GroupFilterMode.Any else min
            filtered_nodes = [
                node for node in graph.nodes if prev_filter_func(node.prevalence.values()) >= self.min_prevalence
            ]
        else:
            filtered_nodes = graph.nodes
        if self.max_missing < 1:
            missing_filter_func = min if self.max_missing_mode == GroupFilterMode.Any else max
            filtered_nodes = [
                node for node in filtered_nodes if missing_filter_func(node.missing.values()) <= self.max_missing
            ]

        if len(filtered_nodes) == 0:
            return AttributeAssociationGraph()

        # only one group, filter only for maximum prevalence
        if len(filtered_nodes[0].groups) == 1:
            nodes_with_scores = [(node, (max(node.prevalence.values()),)) for node in filtered_nodes]
        else:
            nodes_with_scores = [(node, (max(node.prevalence.values()), node.prevalence_difference, node.prevalence_ratio))
                                 for node in filtered_nodes]
        result_nodes = self.__apply_filter_to_list(nodes_with_scores, self.node_comp_ratio, self.perc_nof_nodes,
                                                   self.max_nof_nodes)

        result_ids = {node.node_id for node in result_nodes}

        edge_filter_func = max if self.min_cond_prevalence_mode == GroupFilterMode.Any else min
        if self.min_cond_prevalence > 0:
            min_filtered_edges = [edge for edge in graph.edges
                                  if edge.source in result_ids and edge.target in result_ids
                                  and edge_filter_func(edge.conditional_prevalence.values()) >= self.min_cond_prevalence]
        else:
            min_filtered_edges = [edge for edge in graph.edges
                                  if edge.source in result_ids and edge.target in result_ids]

        if len(min_filtered_edges) == 0:
            return AttributeAssociationGraph(result_nodes)

        increase_score = math.fabs if self.include_conditional_decrease else (lambda x : x)
        increase_ratio_score = ((lambda x : x if x >= 1 else 1/x if x > 0 else math.inf)
                                if self.include_conditional_decrease else (lambda x : x))

        edges_with_scores = [(edge, (max(edge.conditional_prevalence.values()),
                                     max([increase_score(entry) for entry in edge.conditional_increase.values()]),
                                     max([increase_ratio_score(entry) for entry in edge.increase_ratio.values()])))
                             for edge in min_filtered_edges]
        result_edges = self.__apply_filter_to_list(edges_with_scores, self.edge_comp_ratio, self.perc_nof_edges,
                                                   self.max_nof_edges)

        return AttributeAssociationGraph(result_nodes, result_edges)

    @staticmethod
    def __apply_filter_to_list(to_filter : List[Tuple[Union[AttributeAssociationNode, AttributeAssociationEdge], Tuple[float,...]]],
                               composition : Tuple[float, float, float], max_percentage : float, max_count : Optional[int]):
        nof_results = math.ceil(max_percentage * len(to_filter))
        if max_count is not None:
            nof_results = min(nof_results, max_count)
        to_filter.sort(key=lambda x: x[1][0], reverse=True)
        # only one metric calculated (for nodes in graphs with only one group)
        if len(to_filter[0][1]) == 1:
            nof_high_first_score = nof_results
        else:
            nof_high_first_score = math.floor(nof_results * composition[0])
        result = [to_filter[idx][0] for idx in range(nof_high_first_score)]
        if nof_high_first_score < nof_results:
            remaining = to_filter[nof_high_first_score:]
            remaining.sort(key=lambda x: x[1][1], reverse=True)
            nof_high_second_score = min(math.ceil(nof_results * composition[1]), len(remaining))
            result += [remaining[idx][0] for idx in range(nof_high_second_score)]
            if len(result) < nof_results:
                remaining = remaining[nof_high_second_score:]
                remaining.sort(key=lambda x: x[1][2], reverse=True)
                nof_high_third_score = min(nof_results - len(result), len(remaining))
                result += [remaining[idx][0] for idx in range(nof_high_third_score)]
        return result

class ThresholdFilter:
    """This class is an abstract parent for classes filtering
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationNode` and
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdge` objects by parameter thresholds.
    """
    def is_valid(self, obj_to_filter : Union[AttributeAssociationNode, AttributeAssociationEdge]) -> bool:
        """Checks the given filter criteria.

        :param obj_to_filter: The object to filter
        :return: Returns ``True``, if the object passed the filter criteria, ``False`` otherwise
        """
        raise NotImplemented('Never call parent class')

AVAILABLE_PARAMS = {
    'count' : (0, None, True),
    'missing' : (0.0, 1.0, True),
    'prevalence' : (0.0, 1.0, True),
    'prevalence_difference' : (0.0, 1.0, False),
    'prevalence_ratio' : (1.0, None, False),
    'co_occurrence' : (0, None, True),
    'conditional_prevalence' : (0.0, 1.0, True),
    'conditional_increase' : (-1.0, 1.0, True),
    'increase_ratio' : (0.0, None, True)
}

class ThresholdParamFilter(ThresholdFilter):
    """This class filters one specific parameter of a
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationNode` or
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdge` object and checks if the parameter
    value  lies in the
    interval [``min_val``; ``max_val``]. If the property is group dependent, the filter mode must be specified.

    :param param_to_filter: The value for which will be filtered. Must be a statistical parameter of
        :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationNode` or
        :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdge`
    :param min_val: The lowest allowed property value to pass the filter, defaults to None
    :param max_val: The highest allowed property value to pass the filter, defaults to None
    :param mode: The filter mode required for group-dependent parameters. Specifies, if all or only one group value
        must meet the filter thresholds. Defaults to None
    """
    def __init__(self, param_to_filter : str, min_val : Optional[Union[int, float]] = None,
                 max_val : Optional[Union[int, float]] = None, mode : Optional[GroupFilterMode] = None):
        """Constructor method
        """
        super().__init__()
        if param_to_filter not in AVAILABLE_PARAMS:
            raise AttributeError('Parameter "' + param_to_filter
                                 + '" not recognized for filtering, available parameters are: "'
                                 + '", "'.join(AVAILABLE_PARAMS.keys()))
        self.param_to_filter = param_to_filter
        possible_min, possible_max, mode_required = AVAILABLE_PARAMS[self.param_to_filter]
        if min_val is not None and possible_min is not None and min_val < possible_min:
            raise AttributeError('For the filtering of parameter "' + self.param_to_filter
                                 + '" the smallest possible lower bound is ' + str(possible_min)
                                 + ', but ' + str(min_val) + ' was specified')
        self.min_val = min_val if min_val is not None and (possible_min is None or min_val > possible_min) else None
        if max_val is not None and possible_max is not None and max_val > possible_max:
            raise AttributeError('For the filtering of parameter "' + self.param_to_filter
                                 + '" the largest possible upper bound is ' + str(possible_max)
                                 + ', but ' + str(max_val) + ' was specified')
        self.max_val = max_val if max_val is not None and (possible_max is None or max_val < possible_max) else None
        if mode_required and mode is None:
            raise AttributeError('You have to specify the filter mode, since "' + param_to_filter
                                 + '" is a group-dependent parameter')
        self.mode = mode

    def is_valid(self, obj_to_filter : Union[AttributeAssociationNode, AttributeAssociationEdge]) -> bool:
        if not hasattr(obj_to_filter, self.param_to_filter):
            raise AttributeError('Parameter "' + self.param_to_filter + '" does not exist in object of type '
                                 + obj_to_filter.__class__.__name__)
        else:
            param_val = getattr(obj_to_filter, self.param_to_filter)
            # group-defined parameter
            if isinstance(param_val, dict):
                if self.mode is None:
                    raise AttributeError('For group-defined parameter "' + self.param_to_filter
                                         + '" a filter mode must be specified.')
                something_valid = False
                for val in param_val.values():
                    valid = ((self.min_val is None or val >= self.min_val)
                             and (self.max_val is None or val <= self.max_val))
                    if not valid and self.mode == GroupFilterMode.All:
                        return False
                    if valid:
                        something_valid = True
                return something_valid
            else:
                return (self.min_val is None or param_val >= self.min_val) and (
                            self.max_val is None or param_val <= self.max_val)

class ThresholdFilterCascade(ThresholdFilter):
    """This class contains a list of sub-filters (also :class:`ThresholdFilter` objects) which are each apply
    consecutively. Is either a conjunction or disjunction.

    :param filters: The sub-filters
    """
    def __init__(self, filters : Optional[Iterable[ThresholdFilter]] = None):
        super().__init__()
        self.filters = []
        if filters is not None:
            for filter_to_add in filters:
                self.add_filter(filter_to_add)

    def add_filter(self, filter_to_add : ThresholdFilter) -> bool:
        """Add a filter to the cascade. The filter is only added, if it imposes a real constraint.

        :param filter_to_add: The filter that should be added to the cascade
        :return: Return `True`, if the filter imposes a constraint and was added, `False` otherwise
        """
        if isinstance(filter_to_add, ThresholdFilterCascade):
            if len(filter_to_add.filters) == 0:
                return False
            self.filters.append(filter_to_add)
            return True
        elif isinstance(filter_to_add, ThresholdParamFilter):
            # filter does not impose a constraint
            # not necessary to check
            if filter_to_add.min_val is None and filter_to_add.max_val is None:
                return False
            self.filters.append(filter_to_add)
            return True
        else:
            raise NotImplemented('Child class not implemented')

    def is_valid(self, obj_to_filter : Union[AttributeAssociationNode, AttributeAssociationEdge]) -> bool:
        raise NotImplementedError('Never call parent class')

class AndThresholdFilterCascade(ThresholdFilterCascade):
    """This class checks if all its sub-filter criteria are fulfilled (conjunction).

    :param filters: The sub-filters
    """
    def __init__(self, filters: Optional[Iterable[ThresholdFilter]] = None):
        super().__init__(filters)

    def is_valid(self, obj_to_filter: Union[AttributeAssociationNode, AttributeAssociationEdge]) -> bool:
        for filter_mem in self.filters:
            if not filter_mem.is_valid(obj_to_filter):
                return False
        return True

class OrThresholdFilterCascade(ThresholdFilterCascade):
    """This class checks if at least one of its sub-filter criteria are fulfilled (disjunction).

    :param filters: The sub-filters
    """
    def __init__(self, filters: Optional[Iterable[ThresholdFilter]] = None):
        super().__init__(filters)

    def is_valid(self, obj_to_filter: Union[AttributeAssociationNode, AttributeAssociationEdge]) -> bool:
        for filter_mem in self.filters:
            if filter_mem.is_valid(obj_to_filter):
                return True
        return False

