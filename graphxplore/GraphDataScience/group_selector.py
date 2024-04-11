import collections
from typing import Iterable, Dict, List, Tuple
from graphxplore.MetaDataHandling import MetaData
from graphxplore.DataMapping import MetaLattice, AggregatorType
from graphxplore.DataMapping.Conditionals import (LogicOperator, AggregatorOperator, InListOperator, StringOperatorType,
                                                  MetricOperatorType, AndOperator, OrOperator, AtomicOperator,
                                                  AlwaysTrueOperator, NegatedOperator)

class GroupSelector:
    """This class generates Cypher statements to select a group of primary keys (e.g. patient IDs) from a Neo4J
    database based on a :class:`~graphxplore.DataMapping.Conditionals.LogicOperator` object. Variables from
    inverted foreign table chains can be aggregated, and variables from foreign table chains can be used for
    singular comparison. Negations, conjunctions and disjunctions can be used as well.

    :param group_table: The name of the origin table for the group to select
    :param meta: The metadata of the database
    :param group_filter: The conditional describing the group, defaults to the tautology (all primary keys of
        ``group_table`` will be selected)
    """
    def __init__(self, group_table : str, meta : MetaData, group_filter : LogicOperator = AlwaysTrueOperator()):
        """Constructor method
        """
        if group_table not in meta.get_table_names():
            raise AttributeError('Group table "' + group_table + '" not found in metadata')
        self.group_table = group_table
        self.meta = meta
        self.required_children = collections.defaultdict(lambda : collections.defaultdict(list))
        self.required_ancestors = collections.defaultdict(lambda : collections.defaultdict(list))
        full_lattice = MetaLattice.from_meta_data(self.meta)
        if not isinstance(group_filter, AlwaysTrueOperator):
            upward = set(full_lattice.get_relatives(self.group_table))
            upward.add(self.group_table)
            downward = set(full_lattice.get_relatives(self.group_table, upward=False))
            queue = [group_filter]
            while len(queue) > 0:
                current = queue.pop(0)
                if isinstance(current, AndOperator) or isinstance(current, OrOperator):
                    queue += current.sub_operators
                elif isinstance(current, NegatedOperator):
                    queue.append(current.pos_operator)
                elif isinstance(current, AtomicOperator):
                    if current.table not in self.meta.get_table_names():
                        raise AttributeError('Filter table "' + current.table + '" not found in metadata')
                    if current.variable not in self.meta.get_variable_names(current.table):
                        raise AttributeError('Filter variable "' + current.variable + '" not found for "'
                                             + current.table + '" in metadata')
                    var_info = self.meta.get_variable(current.table, current.variable)
                    if current.data_type != var_info.data_type:
                        raise AttributeError('Filter data type "' + current.data_type
                                             + '" does not match data type of variable "' + current.variable
                                             + '" for "' + current.table + '" in metadata')
                    if isinstance(current, AggregatorOperator):
                        if current.table not in downward:
                            raise AttributeError('Filter table "' + current.table
                                                 + '" is marked for aggregation, but has no foreign table chain to '
                                                   'group table "' + group_table + '"')
                        self.required_ancestors[current.table][current.variable].append(current)
                    else:
                        if current.table not in upward:
                            raise AttributeError('group table "' + group_table
                                                 + '" has no foreign table chain to filter table "' + current.table
                                                 + '"')
                        self.required_children[current.table][current.variable].append(current)
                elif isinstance(current, AlwaysTrueOperator):
                    pass
                else:
                    raise  NotImplementedError('Condition not implemented')

        self.group_filter = group_filter
        self.children_lattice = full_lattice.get_sub_lattice_whitelist([self.group_table], self.required_children.keys())
        # inverted lattice
        self.ancestor_lattice = MetaLattice(full_lattice.get_ancestor_lattice([self.group_table], self.required_ancestors.keys()).parents)

    def get_cypher_query(self) -> str:
        """Generates the Cypher query to select the primary keys for the group.

        :return: Returns the generated query as a string
        """
        query = 'match (x_0:' + self.group_table + ' {name:"' + self.meta.get_primary_key(self.group_table) + '"}) where x_0:Key\n'

        path_vars = {self.group_table: 'x_0'}
        attr_vars = collections.defaultdict(dict)
        path_var_counter = 1
        attr_var_counter = 0

        for lattice, required_tables in [(self.children_lattice, self.required_children),
                                         (self.ancestor_lattice, self.required_ancestors)]:
            if len(required_tables) == 0:
                continue
            shortest_paths = lattice.get_shortest_paths_to_required(self.group_table, required_tables.keys())
            shortest_paths_sorted = sorted(shortest_paths.items(), key=lambda x : len(x[1]))
            for required, path in shortest_paths_sorted:
                sub_query = ''
                if required != self.group_table:
                    first_unvisited_idx = len(path)
                    for idx in range(len(path)):
                        if path[idx] not in path_vars:
                            first_unvisited_idx = idx
                            break
                    sub_query += 'match (' + path_vars[path[first_unvisited_idx - 1]] + ')'
                    for idx in range(first_unvisited_idx, len(path)):
                        curr = path[idx]
                        # only have to name required tables and branching points
                        if curr == required or len(lattice.children[curr]) > 1:
                            curr_var = 'x_' + str(path_var_counter)
                            path_var_counter += 1
                        else:
                            curr_var = ''
                        path_vars[curr] = curr_var
                        curr_label = self.meta.get_label(curr)
                        if curr_label == '':
                            curr_label = curr
                        curr_pk = self.meta.get_primary_key(curr)
                        sub_query += '--(' + curr_var + ':' + curr_label + ' {name:"' + curr_pk + '"})'
                    sub_query += '\n'
                path_var = path_vars[required]
                for var, operators in required_tables[required].items():
                    if var == self.meta.get_primary_key(required):
                        attr_vars[required][var] = path_var
                        continue
                    attr_var = 'y_' + str(attr_var_counter)
                    attr_var_counter += 1
                    attr_vars[required][var] = attr_var
                    allow_empty_aggregation = True
                    for operator in operators:
                        if not isinstance(operator, AggregatorOperator) or operator.aggregator not in [AggregatorType.Count, AggregatorType.Concatenate, AggregatorType.List]:
                            allow_empty_aggregation = False
                            break
                    if allow_empty_aggregation:
                        sub_query += 'optional '
                    sub_query += 'match (' + path_var + ')--(' + attr_var + ':Attribute {name:"' + var + '"})\n'
                query += sub_query

        return query + self._get_with_where_clause(attr_vars) + 'return id(x_0) as x_0'

    def _get_with_where_clause(self, attrs_vars : Dict[str, Dict[str, str]]) -> str:
        """Generates the last part containing the potential aggregation and condition checking in a where statement

        :param attrs_vars: The variable names used in the Cypher statement for each combination of table and variable
            in the metadata
        :return: Returns the last query part as string
        """
        result = 'with x_0'
        children_cypher_vars = []
        for table, var_dict in self.required_children.items():
            for var, operators in var_dict.items():
                cypher_var = attrs_vars[table][var]
                if cypher_var != 'x_0':
                    children_cypher_vars.append(cypher_var)
        if len(children_cypher_vars) > 0:
            result += ',' + ','.join(sorted(children_cypher_vars))

        agg_vars = {}
        for table, var_dict in self.required_ancestors.items():
            for var, operators in var_dict.items():
                var_to_agg = attrs_vars[table][var] + '.value'
                for operator in operators:
                    lookup_tuple = (table, var, operator.aggregator)
                    if lookup_tuple not in agg_vars:
                        agg_var = 'z_' + str(len(agg_vars))
                        if operator.aggregator == AggregatorType.List:
                            agg_statement = 'collect(distinct ' + var_to_agg + ')'
                        elif operator.aggregator == AggregatorType.Count:
                            agg_statement = 'count(' + var_to_agg + ')'
                        elif operator.aggregator == AggregatorType.Concatenate:
                            agg_statement = 'apoc.text.join(collect(toString(' + var_to_agg + ')), ";")'
                        elif operator.aggregator == AggregatorType.Sum:
                            agg_statement = 'sum(' + var_to_agg + ')'
                        elif operator.aggregator == AggregatorType.Min:
                            agg_statement = 'min(' + var_to_agg + ')'
                        elif operator.aggregator == AggregatorType.Max:
                            agg_statement = 'max(' + var_to_agg + ')'
                        elif operator.aggregator == AggregatorType.Mean:
                            agg_statement = 'avg(' + var_to_agg + ')'
                        elif operator.aggregator == AggregatorType.Std:
                            agg_statement = 'stDev(' + var_to_agg + ')'
                        elif operator.aggregator == AggregatorType.Median:
                            agg_statement = 'apoc.agg.median(' + var_to_agg + ')'
                        elif operator.aggregator == AggregatorType.Amplitude:
                            agg_statement = 'max(' + var_to_agg + ')-min(' + var_to_agg + ')'
                        else:
                            raise NotImplementedError('Aggregator type not implemented')
                        agg_vars[lookup_tuple] = agg_var
                        result += ',' + agg_statement + ' as ' + agg_var

        result += '\n'

        where_condition = self._get_cypher_condition(self.group_filter, attrs_vars, agg_vars)
        if where_condition != 'true':
            result += 'where ' + where_condition + '\n'

        return result

    @staticmethod
    def _get_cypher_condition(operator : LogicOperator, attrs_vars : Dict[str, Dict[str, str]],
                              agg_vars : Dict[Tuple[str, str, AggregatorType], str]) -> str:
        """Recursively generates the condition checking of the Cypher statement as a where clause

        :param operator: The condition currently checked in the recursion
        :param attrs_vars: The variable names used in the Cypher statement for each combination of table and variable
            in the metadata
        :param agg_vars: The variables introduced for aggregation
        :return: Returns the where clause as a string
        """
        if isinstance(operator, AlwaysTrueOperator):
            return 'true'
        if isinstance(operator, NegatedOperator):
            return 'not (' + GroupSelector._get_cypher_condition(operator.pos_operator, attrs_vars, agg_vars) + ')'
        if isinstance(operator, AndOperator) or isinstance(operator, OrOperator):
            concatenation = ') or (' if isinstance(operator, OrOperator) else ') and ('
            return '(' + concatenation.join((GroupSelector._get_cypher_condition(sub_operator, attrs_vars, agg_vars) for sub_operator in operator.sub_operators)) + ')'
        if isinstance(operator, AtomicOperator):
            if isinstance(operator, AggregatorOperator):
                to_check = agg_vars[(operator.table, operator.variable, operator.aggregator)]
                if operator.aggregator == AggregatorType.List:
                    val = '"' + operator.value + '"' if isinstance(operator.value, str) else str(operator.value)
                    return val + ' in ' + to_check
            else:
                to_check = attrs_vars[operator.table][operator.variable] + '.value'
                if isinstance(operator, InListOperator):
                    return 'toString(' + to_check + ') in ["' + '","'.join(operator.ordered_white_list) + '"]'

            if isinstance(operator.compare, StringOperatorType):
                comparator = '=' if operator.compare == StringOperatorType.Equals else ' contains '
                val = '"' + operator.value + '"'
            # metric comparison
            else:
                comparator = '=' if operator.compare == MetricOperatorType.Equals else operator.compare
                val = str(operator.value)
            return to_check + comparator + val

        raise AttributeError('Cypher condition not implemented for operator type')




