import itertools
import math

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, Dict, Tuple, Union
import collections
from enum import Enum
from graphxplore.GraphDataScience import GroupSelector
from graphxplore.Basis import GraphDatabaseUtils, GraphType
from graphxplore.MetaDataHandling import MetaData, VariableType, VariableInfo
from graphxplore.DataMapping import MetaLattice

class HistogramYScaleType(str, Enum):
    Count = 'Count'
    Fraction = 'Fraction'

class DashboardBuilder:
    """This class generates plots univariate and bivariate distributions by querying a
    :class:`~graphxplore.Basis.BaseGraph.BaseGraph` stored in a Neo4J database. The plots are generated using the
    plotly package. Additionally, subgroups of ``main_table`` primary keys can be defined to jointly plot and compare
    distributions of groups.

    :param meta: The metadata of the :class:`~graphxplore.Basis.BaseGraph.BaseGraph`
    :param main_table: The origin table of primary keys used for the plot
    :param base_graph_database: The name of the :class:`BaseGraph` Neo4J database
    :param full_table_group: If ``True``, all primary keys of ``main_table`` are used as a group. Defaults to
        ``True``
    :param groups: Dictionary of name and :class:`~graphxplore.GraphDataScience.GroupSelector` for the defined
        subgroups. Must have ``main_table`` as their group table. Defaults to None
    :param address: The address of the Neo4J DBMS
    :param auth: User and password of the Neo4J DBMS
    """
    def __init__(self, meta: MetaData, main_table: str, base_graph_database: str, full_table_group: bool = True,
                 groups: Optional[Dict[str, GroupSelector]] = None, address: str = GraphDatabaseUtils.get_neo4j_address(),
                 auth: Tuple[str, str] = ('neo4j', '')):
        """Constructor method
        """
        if main_table not in meta.get_table_names():
            raise AttributeError('Main table "' + main_table + '" of dashboard not in specified metadata')
        self.meta = meta
        self.main_table = main_table
        if not full_table_group and (groups is None or len(groups) == 0):
            raise AttributeError('You have to either specify at least one group, or set the flag "full_table_group" so '
                                 'at least one group will be present')
        self.full_table_group = full_table_group
        if groups is not None:
            for group_name, group_selector in groups.items():
                if group_selector.group_table != main_table:
                    raise AttributeError('Group table of group "' + group_name
                                         + '" does not match main table of dashboard builder')
                if group_selector.meta.to_dict() != self.meta.to_dict():
                    raise AttributeError('Metadata of group "' + group_name
                                         + '" does not match metadata of dashboard builder')
            self.groups = groups
        else:
            self.groups = {}
        if self.full_table_group:
            self.groups['All of table "' + self.main_table + '"'] = GroupSelector(self.main_table, self.meta)
        if GraphDatabaseUtils.check_graph_type_of_db(base_graph_database, address, auth) != GraphType.Base:
            raise AttributeError('Database "' + base_graph_database + '" does not contain a base graph')
        self.base_graph_database = base_graph_database
        self.address = address
        self.auth = auth
        self.lattice = MetaLattice.from_meta_data(self.meta)
        self.group_size = None
        self.group_ids = None

    def get_variable_dist_plot(self, table: str, variable: str,
                               y_scale_type: Optional[HistogramYScaleType] = None) -> go.Figure:
        """Generates a :class:`plotly.graph_objects.Figure` for the univariate distribution of ``variable``. If
        ``variable`` is metric, a plot of multiple histograms (one for each group) is generated. If ``variable`` is
        categorical, multiple pie charts are generated and combined into one plot. All necessary data is queried from
        the Neo4J database

        :param table: the table of the variable
        :param variable: The variable for the distribution plot
        :param y_scale_type: The y-scale type. If group sizes are very imbalanced, ``HistogramYScaleType.Fraction``
            should be preferred
        :return: Returns the plotted figure which can e.g. be used in streamlit or notebooks
        """
        if table != self.main_table and table not in self.lattice.get_relatives(self.main_table):
            raise AttributeError('"' + table + '" is not a foreign table (or foreign table of foreign table...) of "'
                                 + self.main_table + '"')
        var_info = self.meta.get_variable(table, variable)
        if var_info.variable_type not in [VariableType.Metric, VariableType.Categorical]:
            raise AttributeError('Can only plot distribution for metric and categorical variables')
        if var_info.variable_type == VariableType.Metric:
            if y_scale_type is None:
                raise AttributeError('For histogram plots of metric variables, the y-scale type must be specified')

        dist_data = self._query_and_transform_dist_data(var_info)

        if var_info.variable_type == VariableType.Metric:
            hist_norm = None if y_scale_type == HistogramYScaleType.Count else 'probability'
            return px.histogram(
                dist_data, x=variable, color='group', barmode='overlay', histnorm=hist_norm, marginal='box')
        else:
            group_indices, nof_rows, nof_cols = self._get_subplot_indices()
            specs = [[{'type': 'domain'} for i in range(nof_cols)] for j in range(nof_rows)]
            fig = make_subplots(
                rows=nof_rows, cols=nof_cols, specs=specs,
                subplot_titles=tuple([group + ' (' + str(count) + ')' for group, count in self.group_size.items()]))
            for group in self.groups.keys():
                row, col = group_indices[group]
                labels = list(dist_data[group].keys())
                values = list(dist_data[group].values())
                fig.add_trace(go.Pie(labels=labels, values=values, name=group), row, col)
            fig.update_traces(textinfo='label+value')
            fig.update_layout(legend_title_text='Categories of ' + variable)
            return fig

    def get_correlation_plot(self, first_table: str, first_var: str, second_table: str, second_var: str) -> go.Figure:
        """Generates a :class:`plotly.graph_objects.Figure` for the bivariate distribution of ``first_variable`` and
        ``second_variable``. For two metric variables a scatter plot is generated, for a pair of metric and categorical
        variables multiple box plots are generated, and for two categorical variables stacked bar plots are used. All
        necessary data is queried from
        the Neo4J database

        :param first_table: The table of ``first_var``
        :param first_var: The first variable for the distribution
        :param second_table: The table of ``second_var``
        :param second_var: The second variable for the distribution
        :return: Returns the plotted figure which can e.g. be used in streamlit or notebooks
        """
        children = self.lattice.get_relatives(self.main_table)
        for table in [first_table, second_table]:
            if table != self.main_table and table not in children:
                raise AttributeError(
                    '"' + table + '" is not a foreign table (or foreign table of foreign table...) of "'
                    + self.main_table + '"')
        first_var_info = self.meta.get_variable(first_table, first_var)
        second_var_info = self.meta.get_variable(second_table, second_var)
        for var_info in [first_var_info, second_var_info]:
            if var_info.variable_type not in [VariableType.Metric, VariableType.Categorical]:
                raise AttributeError('Can only plot correlation for metric and categorical variables')


        dist_data = self._query_and_transform_dist_data((first_var_info, second_var_info))

        if first_var_info.variable_type == VariableType.Categorical and second_var_info.variable_type == VariableType.Categorical:
            color_dict = {}
            color_iter = itertools.cycle(px.colors.qualitative.Plotly + px.colors.qualitative.Pastel1)
            for second_val in dist_data.keys():
                color_dict[second_val] = next(color_iter)

            group_indices, nof_rows, nof_cols = self._get_subplot_indices()

            fig = make_subplots(
                rows=nof_rows, cols=nof_cols, x_title=first_var,
                subplot_titles=tuple([group + ' (' + str(count) + ')' for group, count in self.group_size.items()]))
            first_group = True
            for group in self.groups.keys():
                row, col = group_indices[group]
                for second_val, data in dist_data.items():
                    x_values, y_values = zip(*data[group].items())
                    fig.add_trace(go.Bar(x=x_values, y=y_values, name=second_val,
                                         hoverinfo='name+y+x', marker_color=color_dict[second_val],
                                         legendgroup=str(second_val), showlegend=True if first_group else False), row,
                                  col)
                first_group = False

            fig.update_xaxes(type='category')
            fig.update_layout(barmode='stack', yaxis_title='Count',
                              legend_title_text='Categories of ' + second_var)
            return fig

        else:
            if first_var_info.variable_type == VariableType.Metric and second_var_info.variable_type == VariableType.Metric:
                return px.scatter(dist_data, x=first_var, y=second_var, color='group',
                                  marginal_x='histogram', marginal_y='histogram')
            elif first_var_info.variable_type == VariableType.Metric:
                return px.box(dist_data, x=second_var, y=first_var, color='group')
            else:
                return px.box(dist_data, x=first_var, y=second_var, color='group')

    def _get_subplot_indices(self) -> Tuple[Dict[str, Tuple[int, int]], int, int]:
        """Generates alignment and indices of subplots for the groups

        :return: Returns a dictionary with row and column index for each group, and number of rows and columns
        """
        nof_cols = min(len(self.groups), 4)
        nof_rows = math.ceil(len(self.groups) / 4)
        result = {}
        # plotly subplots are 1-indexed
        curr_row = 1
        curr_col = 1
        for group in self.groups.keys():
            result[group] = (curr_row, curr_col)
            if curr_col == nof_cols:
                curr_row += 1
                curr_col = 1
            else:
                curr_col += 1
        return result, nof_rows, nof_cols

    def _get_cypher_query(self, var_info: Union[VariableInfo, Tuple[VariableInfo, VariableInfo]]) -> str:
        """Generates the Neo4J Cypher query to retrieve the data for the univariate or bivariate distribution

        :param var_info: Either one variable info for univariate, or two infos for bivariate distributions
        :return: Returns the query as string
        """
        if isinstance(var_info, VariableInfo):
            shortest_path = self.lattice.get_shortest_paths_to_required(
                self.main_table, [var_info.table])[var_info.table]
            query = 'match ' + '--'.join(('(x_' + str(i) + ':' + shortest_path[i] + ')'
                                          for i in range(len(shortest_path))))
            query += ('--(y:' + var_info.table + ' {name:"' + var_info.name
                      + '"}) where x_0:Key return y.value as val, id(x_0) as member_id')
            return query
        else:
            first_info, second_info = var_info
            shortest_paths = self.lattice.get_shortest_paths_to_required(
                self.main_table, [first_info.table, second_info.table])
            first_shortest = shortest_paths[first_info.table]
            second_shortest = shortest_paths[second_info.table]
            last_common_idx = 0
            for path_idx in range(min(len(first_shortest), len(second_shortest))):
                if first_shortest[path_idx] == second_shortest[path_idx]:
                    last_common_idx = path_idx
                else:
                    break
            query = 'match ' + '--'.join(('(x_' + str(i) + ':' + first_shortest[i] + ')'
                                          for i in range(len(first_shortest))))
            query += ('--(y_0:' + first_info.table + ' {name:"' + first_info.name + '"}) where x_0:Key ')
            query += ' match ' + '--'.join(('(' + ('x' if i == last_common_idx else 'z')
                                            + '_' + str(i) + (':' + second_shortest[i] if i > last_common_idx else '')
                                            + ')'
                                            for i in range(last_common_idx, len(second_shortest))))
            query += '--(y_1:' + second_info.table + ' {name:"' + second_info.name + '"}) '
            query += 'return y_0.value as first_val, y_1.value as second_val, id(x_0) as member_id'
            return query

    def _query_and_transform_dist_data(self, var_info: Union[VariableInfo, Tuple[VariableInfo, VariableInfo]]) -> Dict:
        """Queries the Neo4J database for the distribution data and transforms it into the suitable format for plotly

        :param var_info: Either one variable info for univariate, or two infos for bivariate distributions
        :return: Returns the transformed data as dictionary of different formats depending on the variable types and
            quantities
        """
        if self.group_size is None:
            self._query_group_members()

        query = self._get_cypher_query(var_info)
        records = GraphDatabaseUtils.execute_query(
            query=query, database=self.base_graph_database, address=self.address, auth=self.auth)

        if isinstance(var_info, VariableInfo):
            if var_info.variable_type == VariableType.Metric:
                result = {var_info.name: [], 'group': []}
                for record in records:
                    member_id = record['member_id']
                    var_val = record['val']
                    for group in self.group_ids[member_id]:
                        result[var_info.name].append(var_val)
                        result['group'].append(group + ' (' + str(self.group_size[group]) + ')')
                return result
            else:
                result = {group: collections.defaultdict(int) for group in self.groups.keys()}
                for record in records:
                    member_id = record['member_id']
                    var_val = record['val']
                    for group in self.group_ids[member_id]:
                        result[group][var_val] += 1
                return result
        else:
            first_info, second_info = var_info
            if first_info.variable_type == VariableType.Categorical and second_info.variable_type == VariableType.Categorical:
                all_first_vals = set()
                triplets = collections.defaultdict(
                    lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
                for record in records:
                    member_id = record['member_id']
                    first_val = record['first_val']
                    all_first_vals.add(first_val)
                    second_val = record['second_val']
                    for group in self.group_ids[member_id]:
                        triplets[second_val][group][first_val] += 1
                # fill up missing data with zeros and order
                result = {}
                first_val_list = list(all_first_vals)
                for second_val, data in triplets.items():
                    filled_data = {}
                    for group in self.groups.keys():
                        group_data = {first_val : 0 if group not in data or first_val not in data[group]
                        else data[group][first_val]
                                       for first_val in first_val_list}
                        filled_data[group] = group_data
                    result[second_val] = filled_data
                return result
            else:
                result = {first_info.name: [], second_info.name: [], 'group': []}
                for record in records:
                    member_id = record['member_id']
                    first_var_val = record['first_val']
                    second_var_val = record['second_val']
                    for group in self.group_ids[member_id]:
                        result[first_info.name].append(first_var_val)
                        result[second_info.name].append(second_var_val)
                        result['group'].append(group + ' (' + str(self.group_size[group]) + ')')
                return result


    def _query_group_members(self):
        """Queries the Neo4J node IDs for all groups and stores them in the object
        """
        group_ids = collections.defaultdict(list)
        group_size = {}
        for group_name, group_selector in self.groups.items():
            records = GraphDatabaseUtils.execute_query(
                query=group_selector.get_cypher_query(), database=self.base_graph_database, address=self.address,
                auth=self.auth)
            group_size[group_name] = len(records)
            for record in records:
                group_ids[record['x_0']].append(group_name)
        self.group_size = group_size
        self.group_ids = group_ids

