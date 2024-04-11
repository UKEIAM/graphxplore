import contextlib
import copy
import math
import re
try:
    import pyodide.http
    USE_PYODIDE = True
except (ModuleNotFoundError, ImportError):
    import neo4j
    from neo4j import GraphDatabase, exceptions
    USE_PYODIDE = False
import collections
import itertools
from typing import List, Tuple, Union, Optional, Dict, Any

from graphxplore.Basis import GraphDatabaseUtils
from graphxplore.Basis.BaseGraph import BinBoundInfo
from graphxplore.Basis.AttributeAssociationGraph import *
from .group_selector import GroupSelector
from .pre_filter import AttributeAssociationGraphPreFilter
from .post_filter import AttributeAssociationGraphPostFilter

class AttributeAssociationGraphGenerator:
    """This class extracts statistical measurements for all attributes in a dataset regarding their association with one
    or multiple selected group of primary keys (e.g. patient IDs). Absolute counts. missing value rates and prevalence
    of attributes within groups are calculated and compare by difference and ratio. These parameters are stored in
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationNode` objects. Additionally, conditional
    dependencies between attributes are measured by co-occurrence, conditional prevalence in groups and compared to
    unconditional prevalence. The results are stored in
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdge` objects. For
    more detailed descriptions of the calculated metrics refer to
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationNode` and
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdge`.

    Nodes are labeled based on the prevalence of their attribute in the defined groups and the distinction between
    prevalence. These labels are encoded in the size and color of their node depicting in the Neo4J visualization.
    Additionally, edges are assigned a type based on the distinction between conditional and unconditional prevalence.
    This edge type influences the thickness of the drawn arrow representing the edge.

    The origin dataset must be stored as a :class:`~graphxplore.Basis.BaseGraph.BaseGraph` in a Neo4J database. The considered attributes can be
    pre-filtered by name and value using datatypes, string and numerical comparisons, blacklist and whitelist conditions.
    Additionally, the generated graph can be post-filtered by assessing the calculated statistical measurements. For
    more detailed descriptions of the calculated metrics refer to
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationNode` and
    :class:`~graphxplore.Basis.AttributeAssociationGraph.AttributeAssociationEdge`

    :param db_name: The name of the database
    :param group_selection: For each group of primary keys, the name and selection condition as a
        :class:`GroupSelector` object or as a Cypher query. The node IDs of primary keys must be returned with the
        Cypher variable "x_0" in the form "return id(<node variable>) as x_0"
    :param positive_group: The name of the positive group. Must be contained in ``group_selection`` if defined.
        Attributes which appear more frequently in this group compare to the ``negative_group`` will be label as
        "related" or "highly related" and colored in orange or red in the visualization. Defaults to None
    :param negative_group: The name of the negative group. Must be contained in ``group_selection`` if defined.
        Attributes which appear more frequently in this group compare to the ``positive_group`` will be label as
        "inverse" or "highly inverse" and colored in turquoise or blue in the visualization. Defaults to None
    :param pre_filter: The filter applied to attribute nodes when querying the database, defaults to None
    :param post_filter: The post filter applied to the generated knowledge graph, defaults to None
    :param frequency_thresholds: Thresholds of prevalence for "frequent" and "highly frequent"
        labels, defaults to 0.1 and 0.5
    :param prevalence_diff_thresholds: Thresholds for prevalence difference for
        "related"/"inverse" and "highly related"/"highly inverse" labels, defaults to 0.1 and 0.2
    :param prevalence_ratio_thresholds: Thresholds for prevalence ratio for "related"/"inverse"
        and "highly related"/"highly inverse" labels, defaults to 1.5 and 2.0
    :param cond_increase_thresholds: Thresholds of conditional increase for
        "medium relation" and "high relation" labels, defaults to 0.1 and 0.2
    :param increase_ratio_thresholds: Thresholds of conditional increase ratio for
        "medium relation" and "high relation" labels, defaults to 1.5 and 2.0
    :param address: The address of the Neo4J DBMS. Can be generated with
        :func:`~graphxplore.Basis.GraphDatabaseUtils.get_neo4j_address()`
    :param auth: username and password to access the Neo4j DBMS
    """

    def __init__(self, db_name: str, group_selection: Dict[str, Union[GroupSelector, str]],
                 positive_group : Optional[str] = None, negative_group : Optional[str] = None,
                 pre_filter: Optional[AttributeAssociationGraphPreFilter] = None,
                 post_filter: Optional[AttributeAssociationGraphPostFilter] = None,
                 frequency_thresholds: Tuple[float, float] = (0.1, 0.5),
                 prevalence_diff_thresholds: Tuple[float, float] = (0.1, 0.2),
                 prevalence_ratio_thresholds: Tuple[float, float] = (1.5, 2.0),
                 cond_increase_thresholds: Tuple[float, float] = (0.1, 0.2),
                 increase_ratio_thresholds: Tuple[float, float] = (1.5, 2.0),
                 address : str = GraphDatabaseUtils.get_neo4j_address(),
                 auth: Tuple[str, str] = ("neo4j", "")):
        self.address = address
        self.auth = auth
        self.db_name = db_name
        for group in group_selection.keys():
            if not re.match("^[A-Za-z0-9-_]+$", group):
                raise AttributeError(
                    'Group "' + group + '" should only contain letters, numbers, hyphens and underscores')
        self.group_selection = group_selection
        if positive_group is not None and negative_group is not None and positive_group == negative_group:
            raise AttributeError('Positive and negative group cannot be identical')
        if (positive_group is None) != (negative_group is None):
            raise AttributeError('Either both or none of positive and negative group have be specified')
        if positive_group is not None and positive_group not in self.group_selection:
            raise AttributeError('Positive group "' + positive_group + '" not in listed groups')
        if negative_group is not None and negative_group not in self.group_selection:
            raise AttributeError('Negative group "' + negative_group + '" not in listed groups')
        self.negative_group = negative_group
        self.positive_group = positive_group
        self.pre_filter = pre_filter if pre_filter is not None else AttributeAssociationGraphPreFilter()
        self.post_filter = post_filter
        if max(frequency_thresholds) > 1:
            raise AttributeError('Frequency thresholds must be smaller or equal to 1')
        if min(frequency_thresholds) < 0:
            raise AttributeError('Frequency thresholds must be larger or equal to 0')
        if frequency_thresholds[0] > frequency_thresholds[1]:
            raise AttributeError('Threshold for "frequent" nodes must be smaller or equal to threshold for '
                                 '"highly frequent" nodes')
        self.frequency_thresholds = frequency_thresholds
        if max(prevalence_diff_thresholds) > 1:
            raise AttributeError('Prevalence difference thresholds must be smaller or equal to 1')
        if min(prevalence_diff_thresholds) < 0:
            raise AttributeError('Prevalence difference thresholds must be larger or equal to 0')
        if prevalence_diff_thresholds[0] > prevalence_diff_thresholds[1]:
            raise AttributeError('Prevalence difference threshold for "related/inverse" nodes must be smaller or equal to '
                                 'threshold for "highly related/inverse" nodes')
        self.prevalence_diff_thresholds = prevalence_diff_thresholds
        if min(prevalence_ratio_thresholds) < 1:
            raise AttributeError('Prevalence ratio thresholds must be larger or equal to 1')
        if prevalence_ratio_thresholds[0] > prevalence_ratio_thresholds[1]:
            raise AttributeError('Prevalence ratio threshold for "related/inverse" nodes must be smaller or equal to '
                                 'threshold for "highly related/inverse" nodes')
        self.prevalence_ratio_thresholds = prevalence_ratio_thresholds
        if max(cond_increase_thresholds) > 1:
            raise AttributeError('Conditional increase thresholds must be smaller or equal to 1')
        if min(cond_increase_thresholds) < 0:
            raise AttributeError('Conditional increase thresholds must be larger or equal to 0')
        if cond_increase_thresholds[0] > cond_increase_thresholds[1]:
            raise AttributeError('Conditional increase threshold for "medium relation" edges must be smaller or equal to '
                                 'threshold for "high relation" edges')
        self.cond_increase_thresholds = cond_increase_thresholds
        if min(increase_ratio_thresholds) < 1:
            raise AttributeError('Conditional increase ratio thresholds must be larger or equal to 1')
        if increase_ratio_thresholds[0] > increase_ratio_thresholds[1]:
            raise AttributeError('Conditional increase ratio threshold for "medium relation" edges must be smaller or '
                                 'equal to threshold for "high relation" edges')
        self.increase_ratio_thresholds = increase_ratio_thresholds
        self.group_sizes = {}
        self.nodes_with_count = collections.defaultdict(lambda : {group : 0 for group in self.group_selection.keys()})
        self.node_pairs_with_intersection = collections.defaultdict(lambda : {group : 0 for group in self.group_selection.keys()})
        self.variable_counts = collections.defaultdict(lambda: {group: 0 for group in self.group_selection.keys()})
        self.result_graph = AttributeAssociationGraph()
        self.neo4j_driver = None

    def generate_graph(self) -> AttributeAssociationGraph:
        """Generates the graph by first identifying all group primary key nodes, and then retrieving all reachable
        attributes (directly connected or via a path to foreign tables) with a breadth-first search strategy from the
        Neo4J database. Pre and/or post filters are applied if they were specified.

        :return: Returns the generated graph
        """
        available_graphs = GraphDatabaseUtils.get_existing_databases(self.address, self.auth)
        if self.db_name not in available_graphs:
            raise AttributeError(
                'Database "' + self.db_name + '" does not exist under address "' + self.address + '"')
        with contextlib.ExitStack() as stack:
            if USE_PYODIDE:
                driver = None
            else:
                driver = stack.enter_context(GraphDatabase.driver(self.address, auth=self.auth))
            for group, selector in self.group_selection.items():
                print('Processing group "' + group + '"')
                group_nodes = self.__load_group_ids(selector, driver)
                self.group_sizes[group] = len(group_nodes)
                if len(group_nodes) == 0:
                    raise AttributeError('Could not retrieve any members for group "' + group
                                         + '", please check group selection')
                print('"' + group + '" has ' + str(len(group_nodes)) + ' members')
                print('Finding associations in database')
                nof_process = 0
                processed_frac = 0
                for node_id in group_nodes:
                    self.__get_associated_attributes(group, node_id, driver)
                    nof_process += 1
                    new_frac = math.floor(nof_process / len(group_nodes) * 20)
                    if new_frac > processed_frac:
                        processed_frac = new_frac
                        print(str(processed_frac * 5) + '% processed')

        print('Association gathering finished')
        print('Calculating scores and assigning node labels and edge types')
        self._generate_metrics()
        if self.post_filter is not None:
            print('Applying post filters')
            self.result_graph = self.post_filter.filter_graph(self.result_graph)

        print('Generated an attribute association graph with ' + str(len(self.result_graph.nodes)) + ' attributes and '
              + str(len(self.result_graph.edges)) + ' relations between them')
        return self.result_graph

    def __load_group_ids(self, selector : Union[GroupSelector, str], driver : Optional[Any] = None) -> List[int]:
        """Load the primary node IDs from the database based on the :class:`GroupSelector` object or Cypher query.

        :return: A list of primary node indices.
        """
        if isinstance(selector, GroupSelector):
            query = selector.get_cypher_query()
        elif isinstance(selector, str):
            query = selector
            if 'x_0' not in query:
                raise AttributeError('Cypher query must use "x_0" as variable for the node ID of group primary keys')
            return_pattern = re.compile(r'return id\(\w+\) as x_0', re.IGNORECASE)
            matches = return_pattern.findall(query)
            if len(matches) == 0:
                raise AttributeError('Cypher query must end with "return id(<node variable>) as x_0"')
        else:
            raise NotImplementedError('Group selection type not recognized')
        if driver is not None:
            try:
                records, summary, keys = driver.execute_query(query, database_=self.db_name)
                data = [record.data() for record in records]
            except (exceptions.DriverError, exceptions.Neo4jError) as neo4j_error:
                raise AttributeError('Cypher query invalid: "' + query + '", error was: "' +str(neo4j_error) + '"')
        else:
            data = GraphDatabaseUtils.execute_query(query, database=self.db_name, address=self.address, auth=self.auth)
        result = []
        for entry in data:
            if 'x_0' not in entry:
                raise AttributeError('Cypher query must use "x_0" as return variable for node IDs for the group of selected primary keys')
            result.append(entry['x_0'])
        return result

    def __get_associated_attributes(self, group : str, node_id : int, driver : Optional[Any] = None) -> None:
        """Run the generated Cypher query for a single group node on the database and retrieve all connected attribute
        nodes (potentially connected via longer paths i.e. foreign tables)

        :param group: The name of the group the node belongs to
        :param node_id: The ID of the group node
        :param driver: The driver connecting to the Neo4J database
        """
        query = self.pre_filter.get_query(node_id)
        if driver is not None:
            records, summary, keys = driver.execute_query(query, database_=self.db_name)
        else:
            records = GraphDatabaseUtils.execute_query(query, database=self.db_name, address=self.address,
                                                       auth=self.auth)
        attributes = []
        for entry in records:
            labels = AttributeAssociationLabels.from_label_list(entry['labels'])
            bin_info = BinBoundInfo(entry['refRange'][0], entry['refRange'][1]) if entry['refRange'] is not None else None
            node = AttributeAssociationNode(node_id=entry['node_id'], labels=labels,
                                            name=entry['name'], val=entry['value'],
                                            groups=list(self.group_selection.keys()), desc=entry['desc'],
                                            bin_info=bin_info, positive_group=self.positive_group,
                                            negative_group=self.negative_group)
            attributes.append(node)
            self.variable_counts[node.name][group] += 1
            self.nodes_with_count[node][group] += 1

        for first, sec in itertools.combinations(attributes, 2):
            id_pair = (first.node_id, sec.node_id) if first.node_id < sec.node_id else (sec.node_id, first.node_id)
            self.node_pairs_with_intersection[id_pair][group] += 1

    def _generate_metrics(self):
        """Calculate scores for absolute count, missing value ratio and prevalence of attributes. Additionally,
        difference and ratio of prevalence, and labels for the nodes in the generated graph. For edges, the
        co-occurrence count, conditional prevalence, and the absolute and relative conditional increase are calculated
        as well as edge type derived.
        """
        id_node_dict = {}
        for node, group_counts in self.nodes_with_count.items():
            node.group_size = copy.deepcopy(self.group_sizes)
            node.count = copy.deepcopy(group_counts)
            node.missing = {group : round(1 - self.variable_counts[node.name][group]/self.group_sizes[group], 5)
                            for group in node.groups}
            node.prevalence = {group : round(count / self.variable_counts[node.name][group], 5) if count > 0 else 0.0
                               for group, count in group_counts.items()}
            if len(node.groups) > 1:
                if self.positive_group is not None:
                    values = [
                        node.prevalence[self.positive_group], node.prevalence[self.negative_group]
                    ]
                else:
                    values = node.prevalence.values()
                max_val = max(values)
                min_val = min(values)
                node.prevalence_difference = round(max_val - min_val, 5)
                node.prevalence_ratio = AttributeAssociationGraphGenerator.__derive_ratio(max_val, min_val)
            node.labels =  self.__derive_node_labels(node)
            self.result_graph.nodes.append(node)
            id_node_dict[node.node_id] = node

        for id_pair, group_intersections in self.node_pairs_with_intersection.items():
            source_node = id_node_dict[id_pair[0]]
            target_node = id_node_dict[id_pair[1]]
            edge = AttributeAssociationEdge(source=source_node.node_id, target=target_node.node_id,
                                            groups=list(self.group_selection.keys()),
                                            positive_group=self.positive_group, negative_group=self.negative_group,
                                            group_size=copy.deepcopy(self.group_sizes), co_occurrence=group_intersections)
            edge.conditional_prevalence = {
                group : round(co_occur / source_node.count[group], 5) if co_occur > 0 else 0.0
                for group, co_occur in group_intersections.items()}
            edge.conditional_increase = {
                group : round(edge.conditional_prevalence[group] - target_node.prevalence[group], 5)
                for group in edge.groups}
            edge.increase_ratio = {
                group: AttributeAssociationGraphGenerator.__derive_ratio(
                    edge.conditional_prevalence[group], target_node.prevalence[group]
                ) for group in edge.groups}
            edge.edge_type = self.__derive_edge_type(edge)
            self.result_graph.edges.append(edge)
            inverse_edge = AttributeAssociationEdge(source=edge.target, target=edge.source,
                                                    groups=copy.deepcopy(edge.groups),
                                                    positive_group=self.positive_group,
                                                    negative_group=self.negative_group,
                                                    group_size=copy.deepcopy(self.group_sizes),
                                                    co_occurrence=copy.deepcopy(edge.co_occurrence))
            inverse_edge.conditional_prevalence = {
                group : round(co_occur / target_node.count[group], 5) if co_occur > 0 else 0.0
                for group, co_occur in edge.co_occurrence.items()}
            inverse_edge.conditional_increase = {
                group: round(inverse_edge.conditional_prevalence[group] - source_node.prevalence[group], 5)
                for group in inverse_edge.groups}
            inverse_edge.increase_ratio = {
                group: AttributeAssociationGraphGenerator.__derive_ratio(
                    inverse_edge.conditional_prevalence[group], source_node.prevalence[group]
                ) for group in inverse_edge.groups}
            inverse_edge.edge_type = self.__derive_edge_type(inverse_edge)
            self.result_graph.edges.append(inverse_edge)

    def __derive_node_labels(self, node : AttributeAssociationNode) -> AttributeAssociationLabels:
        """Derive labels about frequency of an attribute and additionally distinction, if a positive and
        negative group are provided. The thresholds provided during initialization of the generator are used

        :param node: The node for which labels should be derived
        :return: Returns an :class:`AttributeAssociationsLabels` object with the underlying labels of the node and the
            additional derived labels
        """
        result_labels = node.labels
        frequency = max(node.prevalence.values())
        if frequency < self.frequency_thresholds[0]:
            result_labels.frequency_label = FrequencyLabel.Infrequent
        elif frequency < self.frequency_thresholds[1]:
            result_labels.frequency_label = FrequencyLabel.Frequent
        else:
            result_labels.frequency_label = FrequencyLabel.HighlyFrequent

        if self.positive_group is not None:
            pos_larger = node.prevalence[self.positive_group] > node.prevalence[self.negative_group]
            if (node.prevalence_difference < self.prevalence_diff_thresholds[0]
                    and node.prevalence_ratio < self.prevalence_ratio_thresholds[0]):
                result_labels.distinction_label = DistinctionLabel.Unrelated
            elif (node.prevalence_difference < self.prevalence_diff_thresholds[1]
                  and node.prevalence_ratio < self.prevalence_ratio_thresholds[1]):
                result_labels.distinction_label = DistinctionLabel.Related if pos_larger else DistinctionLabel.Inverse
            else:
                result_labels.distinction_label = (DistinctionLabel.HighlyRelated if pos_larger else
                                                   DistinctionLabel.HighlyInverse)
        return result_labels

    def __derive_edge_type(self, edge : AttributeAssociationEdge) -> AttributeAssociationEdgeType:
        """Derive the type of an :class:`AttributeAssociationEdge` based on its absolute and relative conditional
        increase The type specifies the level of conditional relation the source attribute has on the target attribute.
        The threshold given during the generator initialization are used.

        :param edge: The edge for which the type is inferred
        :return: Returns the derived type
        """
        abs_score = max([math.fabs(entry) for entry in edge.conditional_increase.values()])
        rel_score = max([entry if entry >= 1 else 1/entry
                         for entry in edge.increase_ratio.values() if not math.isnan(entry)])
        if abs_score < self.cond_increase_thresholds[0] and rel_score < self.increase_ratio_thresholds[0]:
            return AttributeAssociationEdgeType.LOW_RELATION
        if abs_score < self.cond_increase_thresholds[1] and rel_score < self.increase_ratio_thresholds[1]:
            return AttributeAssociationEdgeType.MEDIUM_RELATION
        return AttributeAssociationEdgeType.HIGH_RELATION

    @staticmethod
    def __derive_ratio(numerator: Union[int, float], denominator: Union[int, float]) -> float:
        """Calculate the ratio between two numbers. If both are zero, will return 1.0. If only numerator is zero, will
        return NaN. If only denominator is zero, will return infinity (or - infinity)

        :param numerator: The number to be divided
        :param denominator: The number that divides ``numerator``
        :return: Returns the calucated ratio, NaN or  +/- infinity
        """
        if numerator != 0 and denominator != 0:
            return round(numerator/denominator, 5)
        if numerator == 0:
            if denominator == 0:
                return 1.0
            return math.nan
        # denominator is 0, numerator is not 0
        if numerator > 0:
            return math.inf
        return -math.inf

