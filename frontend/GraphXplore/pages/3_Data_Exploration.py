import collections
import json
import chardet
import streamlit as st
import re
import copy
import pandas as pd
import plotly.express as px
from typing import List, Optional, Dict
try:
    import pyodide
    DESKTOP_APP = True
except (ModuleNotFoundError, ImportError):
    DESKTOP_APP = False
import pathlib
BASE_DIR = str(pathlib.Path(__file__).parents[1])
FRONTEND_DIR = str(pathlib.Path(__file__).parents[0])
import sys
sys.path.append(BASE_DIR)
sys.path.append(FRONTEND_DIR)
from src.io_widgets import CSVUploader
from src.list_widgets import EditableList
from src.logical_operator_widgets import ConditionDefinition
from src.utils import (VariableHandle, ICON_PATH, ListHandle, FunctionWrapper, BLOOM_PATH, BROWSER_STYLE_PATH,
                       get_how_to_image_path)
from src.common_state_keys import (NEO4J_ADDRESS_KEY, NEO4J_AUTH_KEY, TRANSLATION_META_KEY, MAIN_META_KEY,
                                   TRANSLATION_SOURCE_DATA_KEY, TRANSLATION_DB_KEY, EXISTING_DATABASES_KEY,
                                   AAG_META_KEY, DEFINED_GROUP_KEY, GROUP_META_KEY, GROUP_LATTICE_KEY, GROUP_LOAD_META,
                                   DASHBOARD_META_KEY, DASHBOARD_DB_KEY, DASHBOARD_BASIS_GROUPS, DASHBOARD_BASIS_TABLE,
                                   AAG_INPUT_DB_KEY, AGG_RESULT_DB_KEY, AAG_CHOSEN_GROUPS, AAG_POS_GROUP, AAG_NEG_GROUP,
                                   AAG_TABLE_DB_KEY, AAG_TABLE_RESULT_KEY, CURR_TASK, DASHBOARD_FIG,
                                   DASHBOARD_BUILDER, AGG_TABLE_GROUPS_KEY)
from src.workflow_widgets import Workflow
from src.sub_tasks import WorkflowGoal, TriggerProcess, LoadGroups, CreateGroup
from graphxplore.Basis import *
from graphxplore.Basis.BaseGraph import *
from graphxplore.Basis.AttributeAssociationGraph import *
from graphxplore.MetaDataHandling import *
from graphxplore.GraphTranslation import *
from graphxplore.DataMapping import AggregatorType, MetaLattice
from graphxplore.DataMapping.Conditionals import *
from graphxplore.GraphDataScience import *
from graphxplore.Dashboard import *

CSV_LINE_THRESHOLD = 10000
DATABASE_READ_EDGE_THRESHOLD = 1000000

def refresh_existing_databases() -> List[str]:
    curr_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
    current_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
    dbs_handle = VariableHandle(EXISTING_DATABASES_KEY)
    dbs_handle.set_attr(GraphDatabaseUtils.get_existing_databases(curr_address, current_auth))
    assign_neo4j_browser_styling()
    return dbs_handle.get_attr()

def assign_connection(parent_obj, neo4j_host, neo4j_port, user_name, user_pw):
    try:
        address = GraphDatabaseUtils.get_neo4j_address(host=neo4j_host, port=neo4j_port)
        GraphDatabaseUtils.test_connection(address, (user_name, user_pw))
        VariableHandle(NEO4J_ADDRESS_KEY).set_attr(address)
        VariableHandle(NEO4J_AUTH_KEY).set_attr((user_name, user_pw))
        refresh_existing_databases()
        parent_obj.success('Connection to Neo4J DBMS established')
    except AttributeError as e:
        parent_obj.error('ERROR: ' + str(e))

def get_neo4j_connection_widget(parent_obj):
    with parent_obj.expander('Assign connection to Neo4J database management system'):
        current_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
        current_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
        if current_address is not None:
            entries = current_address.split('://')[1].split(':')
            default_host = entries[0]
            default_port = int(entries[1])
            default_user = current_auth[0]
            default_pw = current_auth[1]
        else:
            default_host = 'localhost'
            default_port = 7474 if DESKTOP_APP else 7687
            default_user = 'neo4j'
            default_pw = ''
        cont = st.container()
        host_col, port_col = cont.columns(2)
        neo4j_host = host_col.text_input('Neo4J server host', default_host,
                                         help='If accessing GraphXplore remotely, this host must be accessible from '
                                              'the server host' if not DESKTOP_APP else None)
        neo4j_port = port_col.number_input('Neo4J Port', value=default_port,
                                          help='If accessing GraphXplore remotely, this port must be accessible from '
                                               'the server host' if not DESKTOP_APP else None)
        user_col, pw_col = cont.columns(2)
        user_name = user_col.text_input('Username', default_user)
        user_pw = pw_col.text_input('Password', default_pw, type='password')
        cont.button('Assign connection', type='primary', on_click=assign_connection,
                    args=[cont, neo4j_host, neo4j_port, user_name, user_pw])

def select_db(parent_obj, db_name_key: str, databases: List[str], db_name_select: str, graph_type : Optional[GraphType],
              write: bool, overwrite_db: bool, meta_to_check : Optional[MetaData]):
    current_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
    current_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
    if db_name_select == '':
        parent_obj.error('You have to specify a name for the new database')
    elif not re.match('^[a-z][a-z0-9.]*$', db_name_select):
        parent_obj.error('The database name can only contain lower case letters, numbers, and dots')
    elif write and not overwrite_db and db_name_select in databases:
        parent_obj.error('Database already exists')
    else:
        try:
            if not write:
                if graph_type is not None:
                    if graph_type != GraphDatabaseUtils.check_graph_type_of_db(
                            db_name_select, current_address, current_auth):
                        raise AttributeError('Graph type of database "' + db_name_select + '" is not '
                                             + graph_type)
                # if DATABASE_READ_EDGE_THRESHOLD < GraphDatabaseUtils.get_nof_edges_in_database(
                #         db_name_select, current_address, current_auth):
                #     raise AttributeError('Graph type of database "' + db_name_select
                #                          + '" is too large for exploration in frontend. Please refer to '
                #                            'the python package "graphxplore" for handling of large datasets')
                if meta_to_check is not None:
                    if not GraphDatabaseUtils.database_contains_labels(
                            db_name_select, meta_to_check.get_table_names(), current_address, current_auth):
                        raise AttributeError('Database does not match the assigned metadata')
            VariableHandle(db_name_key).set_attr(db_name_select)
            parent_obj.success('Database "' + db_name_select + '" successfully selected')
        except AttributeError as error:
            parent_obj.error('ERROR: ' + str(error))

def get_database_select_widget(parent_obj, db_name_key : str, desc : str, write : bool,
                               graph_type : Optional[GraphType] = None,
                               meta_to_check : Optional[MetaData] = None) -> bool:
    current_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
    current_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
    with parent_obj.expander(desc):
        cont = st.container()
        try:
            #GraphDatabaseUtils.test_connection(current_address, current_auth)
            if write:
                db_action = cont.selectbox('Select action', options=['Create new database', 'Overwrite existing database'],
                                         key=db_name_key + '_action')
            overwrite_db = write and db_action == 'Overwrite existing database'
            dbs_handle = VariableHandle(EXISTING_DATABASES_KEY)
            if dbs_handle.get_attr() is None:
                refresh_existing_databases()
            databases = dbs_handle.get_attr()
            if not write or db_action == 'Overwrite existing database':
                cont.button('Refresh databases', on_click=refresh_existing_databases, key=db_name_key + '_refresh')
                db_name_select = cont.selectbox('Choose database', options=databases, key=db_name_key + '_choose_db')
            else:
                db_name_select = cont.text_input('Insert name of new database', '', key=db_name_key + '_insert_new_name')
            cont.button('Ok', type='primary', key=db_name_key + '_ok', on_click=select_db,
                        args=[cont, db_name_key, databases, db_name_select, graph_type, write, overwrite_db,
                              meta_to_check])
            return overwrite_db

        except AttributeError as error:
            cont.error('ERROR: ' + str(error))
            return False

def assign_metadata(parent_obj, db_name_key: str, meta_key: str, lattice_key: str):
    db_name = VariableHandle(db_name_key).get_attr()
    curr_main_meta = VariableHandle(MAIN_META_KEY).get_attr()
    current_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
    current_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
    if not GraphDatabaseUtils.database_contains_labels(
            db_name, curr_main_meta.get_table_names(), current_address, current_auth):
        parent_obj.error('Metadata does not match base graph')
    else:
        VariableHandle(meta_key).set_attr(copy.deepcopy(curr_main_meta))
        VariableHandle(lattice_key).set_attr(MetaLattice.from_meta_data(curr_main_meta))

def create_group(parent_obj, meta: MetaData, new_group_table: str,
                 new_group_name: str, new_condition: str):
    if not re.match("^[A-Za-z0-9-_]+$", new_group_name):
        raise AttributeError(
            'Group "' + new_group_name + '" should only contain letters, numbers, hyphens and underscores')
    curr_groups = VariableHandle(DEFINED_GROUP_KEY).get_attr()
    if new_group_name in curr_groups:
        parent_obj.error('Group name "' + new_group_name + '" already used')
    else:
        try:
            new_selector = GroupSelector(new_group_table, meta, LogicOperatorParser.from_string(new_condition))
            curr_groups[new_group_name] = new_selector
            parent_obj.success('Group created')
            curr_task = VariableHandle(CURR_TASK).get_attr()
            if curr_task is not None and isinstance(curr_task, CreateGroup):
                curr_task.group_name = new_group_name
        except AttributeError as error:
            parent_obj.error('ERROR: ' + str(error))

def get_generator_advanced_options_widget(parent_obj):
    with parent_obj.expander('Advanced options'):
        pre_filter_tab, post_filter_tab, thresholds_tab = st.tabs(['Pre-filtering', 'Post-filtering',
                                                                   'Label/type thresholds'])
        with pre_filter_tab:
            if st.checkbox('Show pre-filtering tooltip'):
                pre_filter_msg = """
                Here, you can specify filtering criteria on variable names and values which should be included or 
                excluded from the attribute association graph. Only pairs of variable name and value meeting all filter 
                criteria will be added to the graph You can add one or multiple filters choosing from the following 
                options:
                - Filter :red[variable names] by :red[equality, inequality and substring containment]
                - Filter string or numeric variable values:
                    - :red[String values] by :red[equality, inequality and substring containment]
                    - :red[Numeric values] by :red[equality, inequality, or <, <=, >, >= relation]
                    - All values of other data type will be unaffected by the filter criteria
                - For both filter types, choose between :red[inclusion or exclusion criteria]:
                    - :red[Inclusion criteria]: Only variable name/values :red[matching] this criteria will be added to 
                      the graph
                    - :red[Exclusion criteria]: Only variable name/values :red[not matching] this criteria will be 
                      added to the graph
                """
                st.markdown(pre_filter_msg)
            if 'pre_filter' not in st.session_state:
                st.session_state.pre_filter = AttributeAssociationGraphPreFilter(max_path_length=9999)
            if len(st.session_state.pre_filter.name_filters) == 0 and len(
                    st.session_state.pre_filter.value_filters) == 0:
                st.info('No pre-filter defined')
            else:
                if st.button('Fully reset pre-filter', type='primary'):
                    st.session_state.pre_filter = AttributeAssociationGraphPreFilter(max_path_length=9999)
                if len(st.session_state.pre_filter.name_filters) > 0:
                    st.markdown('**Variable name filters**')
                    for idx in range(len(st.session_state.pre_filter.name_filters)):
                        disp_col, remove_col = st.columns(2)
                        name_filter = st.session_state.pre_filter.name_filters[idx]
                        filter_prefix = 'Include if name ' if name_filter.include else 'Exclude if name '
                        name_filter_str = (filter_prefix + str(name_filter)).replace('<>', '!=')
                        disp_col.markdown(name_filter_str)
                        remove_col.button('Remove filter', key='name_filters_' + str(idx),
                                          on_click=st.session_state.pre_filter.name_filters.pop, args=[idx])
                if len(st.session_state.pre_filter.value_filters) > 0:
                    st.markdown('**Variable value filters**')
                    for idx in range(len(st.session_state.pre_filter.value_filters)):
                        disp_col, remove_col = st.columns(2)
                        value_filter = st.session_state.pre_filter.value_filters[idx]
                        filter_prefix = 'Include if ' if value_filter.include else 'Exclude if '
                        filter_prefix = filter_prefix + 'numeric ' if isinstance(value_filter.type,
                                                                   NumericFilterType) else filter_prefix + 'string '
                        filter_prefix += 'value '
                        value_filter_str = (filter_prefix + str(value_filter)).replace('<>', '!=')
                        disp_col.markdown(value_filter_str)
                        remove_col.button('Remove filter', key='value_filters_' + str(idx),
                                          on_click=st.session_state.pre_filter.value_filters.pop, args=[idx])

            st.markdown('**Define filter**')
            filter_type_select = st.radio('Variable name or value filter', ['Name', 'Value'])
            if filter_type_select == 'Name':
                type_col, val_col, incl_col = st.columns(3)
                filter_comp_type = type_col.selectbox('Choose type of name comparison', StringFilterType.__members__)
                filter_comp = StringFilterType._member_map_[filter_comp_type]
                filter_val = val_col.text_input('Insert string to compare against')
                incl_type = incl_col.radio('Choose criteria', ['Inclusion criteria', 'Exclusion criteria'])
            else:
                data_type_col, type_col, val_col, incl_col = st.columns(4)
                data_filter_type = data_type_col.selectbox('Choose datatype of value', ['String', 'Numeric'],
                                                           help='Values of other datatype will not be affected '
                                                                'by this filter')
                if data_filter_type == 'String':
                    filter_comp_type = type_col.selectbox('Choose type of comparison',
                                                          StringFilterType.__members__)
                    filter_comp = StringFilterType._member_map_[filter_comp_type]
                    filter_val = val_col.text_input('Insert string to compare against')
                else:
                    filter_comp_type = type_col.selectbox('Choose type of comparison',
                                                          NumericFilterType.__members__)
                    filter_comp = NumericFilterType._member_map_[filter_comp_type]
                    filter_val = val_col.number_input('Insert string to compare against')

                incl_type = incl_col.radio('Choose criteria', ['Inclusion criteria', 'Exclusion criteria'])

            st.button('Add filter', disabled=filter_val == '', on_click=lambda :
            (st.session_state.pre_filter.name_filters if filter_type_select == 'Name'
             else st.session_state.pre_filter.value_filters).append(AttributeFilter(
                filter_val, filter_comp, incl_type == 'Inclusion criteria')))

        with post_filter_tab:
            if st.checkbox('Show post-filter tooltip'):
                """
                Here, you can specify how GraphXplore will filter the generated nodes and edges of the attribute 
                association graph based on their statistical traits to focus only on patterns of interest in your 
                dataset. To get an overview about the statistical metrics used in attribute association graphs, check 
                out "Data Exploration (sidebar)"->"Data Exploration"->"Intro to Attribute Association Graphs". The 
                filter follows these steps:
                - :red[Threshold filters] are applied to nodes and edges. The threshold must either be met by all or at 
                  least one group
                  - For nodes, the thresholds are :red[minimum prevalence] and :red[maximum missing value ratio]
                  - For edges, the :red[minimum conditional prevalence] is the only threshold
                  - You can de-activate a threshold filter by choosing 0.00 for minimum, and 1.00 for maximum filter 
                    criteria
                - For the remaining nodes and edges passing the threshold filters, you can specify red[a fraction of 
                  objects] that should remain after the next composition filtering step. Optionally, you can specify 
                  :red[a maximum number of objects that should remain]. The minimum remainder will be taken
                - :red[Composition filters] are applied to nodes and edges. The nodes and edges with the highest value 
                  are selected for three different metrics. Afterwards, the ratio you specify here is applied to 
                  compose the resulting graph. The ratio is built based on the following metrics:
                    - :red[High maximum prevalence for nodes, and high maximum conditional prevalence for edges]. 
                      Attributes of these nodes :red[appear frequently] in the group with the highest prevalence, 
                      :red[but are not necessarily selective] for that specific group. For an edge A->B with a high 
                      maximum conditional prevalence, many members with attribute A, also exhibit attribute B in the 
                      group with the highest conditional prevalence. However, B could just have a high prevalence 
                      itself and thus the added condition of A is not necessarily selective for B 
                    - :red[High prevalence difference for nodes, and high conditional increase for edges]. These node's 
                      attributes appear more often in one group compared another in absolute terms. Thus, this 
                      attribute has a :red[high sensitivity] for that group. But they could still have some prevalence in
                      another group, meaning their :red[specificity could be low]. For an edge A->B with a high maximum 
                      conditional increase, The added condition of A has a high sensitivity for the presence of B 
                      in at least one group. However, the prevalence B could be high as well, meaning A would not be 
                      specific for B
                    - :red[High prevalence ratio for nodes, and high conditional increase ratio for edges]. Attributes 
                      of these nodes have a :red[high specificity] for one group compared to another group. But all
                      prevalence could be low resulting in a :red[potentially low sensitivity] of the attribute. For an 
                      edge A->B with a high maximum conditional increase ratio, The added condition of A has a high 
                      specificity for the presence of B in at least one group. However, the conditional prevalence 
                      could be low, meaning A could not be sensitive for the presence of B
                - For edges, you can specify if :red[conditional decrease] should also be included into the 
                  composition. If chosen, edges with high absolute negative conditional increase (meaning conditional 
                  decrease) and high inverted conditional increase ratio are also viewed and "specific" and "sensitive"
                """
            if 'post_filter' not in st.session_state:
                st.session_state.post_filter = CompositionGraphPostFilter()
            st.subheader('Node filter')
            st.slider(
                'Select fraction of nodes that should remain', 0.0, 1.0, 0.5,
                help='This fraction of the nodes passing the minimum prevalence and maximum missing value ratio '
                     'will remain after filtering (or the maximum node number, '
                     'if smaller and marked by you). The composition ratio will be '
                     'applied to this fraction of nodes. If you specify 1.0, only '
                     'the minimum prevalence and maximum missing value ratio will be applied as filter condition',
                key='perc_nodes_slider',
                on_change=lambda : setattr(st.session_state.post_filter, 'perc_nof_nodes',
                                           st.session_state.perc_nodes_slider))
            max_nodes_check_col, max_nodes_select_col = st.columns(2)
            max_nodes_check = max_nodes_check_col.checkbox('Use maximum node number')
            max_nof_nodes_select = max_nodes_select_col.number_input('Insert maximum number of nodes',
                                                                     min_value=1, value=100,
                                                                     disabled=not max_nodes_check)
            if max_nodes_check:
                st.session_state.post_filter.max_nof_nodes = max_nof_nodes_select
            else:
                st.session_state.post_filter.max_nof_nodes = None
            min_prevalence_slider_col, min_prevalence_mode_col = st.columns(2)
            min_prevalence_mode_col.checkbox(
                'Minimum prevalence applied to all groups',
                help='Specify if the minimum prevalence must be met by all groups or only one',
                key='min_prevalence_mode_toggle',
                value=st.session_state.post_filter.min_prevalence_mode == GroupFilterMode.All,
                on_change=lambda : setattr(st.session_state.post_filter, 'min_prevalence_mode',
                                           (GroupFilterMode.All if st.session_state.min_prevalence_mode_toggle
                                            else GroupFilterMode.Any))
            )
            st.session_state.post_filter.min_prevalence = min_prevalence_slider_col.slider(
                'Select minimum prevalence', 0.0, 1.0, 0.01,
                help="The node's attribute must be present in at least this "
                     "ratio of members for all groups (or only one if checkbox on the left is de-selected by you). "
                     "With this filter you can remove very infrequent attributes from your analysis")
            max_missing_slider_col, max_missing_mode_col = st.columns(2)
            max_missing_mode_col.checkbox(
                'Maximum missing value ratio applied to all groups',
                help='Specify if the maximum missing value ratio must be met by all groups or only one',
                key='max_missing_mode_toggle',
                value=st.session_state.post_filter.max_missing_mode == GroupFilterMode.All,
                on_change=lambda: setattr(st.session_state.post_filter, 'max_missing_mode',
                                          (GroupFilterMode.All if st.session_state.max_missing_mode_toggle
                                           else GroupFilterMode.Any))
            )
            st.session_state.post_filter.max_missing = max_missing_slider_col.slider(
                'Select maximum missing value ratio', 0.0, 1.0, st.session_state.post_filter.max_missing,
                help="The node's variable can be missing for at most this "
                     "ratio of members for all groups (or only one if checkbox on the left is de-selected by you). "
                     "With this filter you can remove attributes with a high missing value rate from your analysis")
            node_comp_msg = f"""
            #### Node composition
            - high prevalence: {str(st.session_state.post_filter.node_comp_ratio[0])}
            - high prevalence difference: {str(st.session_state.post_filter.node_comp_ratio[1])}
            - high prevalence ratio : {str(st.session_state.post_filter.node_comp_ratio[2])}
            """
            st.markdown(node_comp_msg)
            st.slider(
                'Select node composition ratio', 0.0, 1.0,
                (st.session_state.post_filter.node_comp_ratio[1],
                 st.session_state.post_filter.node_comp_ratio[1] + st.session_state.post_filter.node_comp_ratio[2]),
                key='node_comp_slider',
                on_change= lambda : setattr(
                    st.session_state.post_filter, 'node_comp_ratio',
                    (round(1.0 - st.session_state.node_comp_slider[1], 2),
                     st.session_state.node_comp_slider[0],
                     round(st.session_state.node_comp_slider[1] - st.session_state.node_comp_slider[0], 2))))

            st.subheader('Edge filter')
            max_edges_tick_col, max_edges_select_col = st.columns(2)
            max_edges_check = max_edges_tick_col.checkbox('Use maximum edge number')
            max_nof_edges_select = max_edges_select_col.number_input('Insert maximum number of edges',
                                                                     min_value=1, value=100,
                                                                     disabled=not max_edges_check)
            if max_edges_check:
                st.session_state.post_filter.max_nof_edges = max_nof_edges_select
            else:
                st.session_state.post_filter.max_nof_edges = None
            st.session_state.post_filter.perc_nof_edges = st.slider(
                'Select fraction of edges that should remain', 0.0, 1.0, 0.25,
                help='This faction of the edges passing the minimum conditional prevalence '
                     'will remain after filtering (or the maximum edge number, '
                     'if smaller and marked by you). The composition ratio will be '
                     'applied to this fraction of edges. If you specify 1.0, only '
                     'the minimum conditional prevalence will be applied as filter condition')
            min_cond_prevalence_slider_col, min_cond_prevalence_mode_col = st.columns(2)
            min_cond_prevalence_mode_col.checkbox(
                'Minimum conditional prevalence applied to all groups',
                help='Specify if minimum conditional prevalence must be met by all groups or only one',
                value=st.session_state.post_filter.min_cond_prevalence_mode == GroupFilterMode.All,
                on_change=lambda : setattr(st.session_state.post_filter, 'min_cond_prevalence_mode',
                                           (GroupFilterMode.All if st.session_state.min_cond_prevalence_mode_toggle
                                            else GroupFilterMode.Any)))
            st.session_state.post_filter.min_cond_prevalence = min_cond_prevalence_slider_col.slider(
                'Select minimum conditional prevalence', 0.0, 1.0, 0.05,
                help="For an edge pointing from attribute A to B, the conditional "
                     "prevalence of group members with attribute A that also have "
                     "attribute B must be at least this value for all groups (or at least one, if check box on the "
                     "left is de-selected by you). With this filter you can remove weak conditional "
                     "relations from your analysis")

            edge_comp_msg = f"""
                        #### Edge composition
                        - high conditional prevalence: {str(st.session_state.post_filter.edge_comp_ratio[0])}
                        - high conditional increase 
                          {'(or decrease)' if st.session_state.post_filter.include_conditional_decrease else ''}
                          : {str(st.session_state.post_filter.edge_comp_ratio[1])}
                        - high 
                          {'(or high inverted)' if st.session_state.post_filter.include_conditional_decrease else ''} 
                          conditional increase ratio : {str(st.session_state.post_filter.edge_comp_ratio[2])}
                        """
            st.markdown(edge_comp_msg)

            st.slider(
                'Select edge composition ratio', 0.0, 1.0,
                (st.session_state.post_filter.edge_comp_ratio[1],
                 st.session_state.post_filter.edge_comp_ratio[1] + st.session_state.post_filter.edge_comp_ratio[2]),
                key='edge_comp_slider',
                on_change=lambda: setattr(
                    st.session_state.post_filter, 'edge_comp_ratio',
                    (round(1.0 - st.session_state.edge_comp_slider[1], 2),
                     st.session_state.edge_comp_slider[0],
                     round(st.session_state.edge_comp_slider[1] - st.session_state.edge_comp_slider[0], 2))))
            st.session_state.post_filter.include_conditional_decrease = st.checkbox(
                'Include conditional decrease in edge composition', help='See composition tooltip for explanation',
                value=st.session_state.post_filter.include_conditional_decrease, key='cond_decrease_check',
                on_change=lambda : setattr(st.session_state.post_filter, 'include_conditional_decrease',
                                           st.session_state.cond_decrease_check))

        with thresholds_tab:
            freq_handle = VariableHandle('freq_thresholds', init=(0.1, 0.5))
            prev_diff_handle = VariableHandle('prevalence_diff_thresholds', init=(0.1, 0.2))
            prev_ratio_handle = VariableHandle('prevalence_ratio_thresholds', init=(1.5, 2.0))
            cond_increase_handle = VariableHandle('cond_increase_thresholds', init=(0.1, 0.2))
            indrease_ratio_handle = VariableHandle('increase_ratio_thresholds', init=(1.5, 2.0))

            st.subheader('Node label thresholds')

            if st.checkbox('Show node label tooltip'):
                node_label_msg = f"""
                GraphXplore labels the nodes of the attribute association graph representing several statistical 
                metrics by labels and shape as well as color of the visualized nodes
                #### Frequency label
                This label expresses how often an attribute is exhibited in your dataset. It will influence the size of 
                the corresponding node in the visualization where more frequent attributes will be indicated by larger 
                spheres. The following labels are assigned:
                  - :red[Highly frequent]: Attributes with a prevalence of 
                    :red[{str(st.session_state.freq_thresholds[1])}] or higher in at least one group
                  - :red[Infrequent]: Attributes with a prevalence smaller than 
                    :red[{str(st.session_state.freq_thresholds[0])}] for all groups 
                  - :red[Frequent]: Remaining attributes
                #### Distinction label
                This label will only be assigned, if your attribute association graph has at least two groups and you 
                assigned a positive and negative group. This label influences the color of the nodes. 
                GraphXplore considers the difference and ratio between prevalence of the positive and negative group:
                  - :red[Unrelated]: The difference is smaller than 
                    :red[{str(st.session_state.prevalence_diff_thresholds[0])}] and the quotient is smaller than 
                    :red[{str(st.session_state.prevalence_ratio_thresholds[0])}]. The node's sphere will be color in beige
                  - :red[Highly related] or :red[highly inverse]: The difference is at least 
                    :red[{str(st.session_state.prevalence_diff_thresholds[1])}] or the ratio is at least 
                    :red[{str(st.session_state.prevalence_ratio_thresholds[1])}]. The attribute will be labeled as 
                    :red[highly related] if the prevalence in the positive group is larger or highly inverse
                    otherwise. Highly related nodes will be colored red, and highly inverse nodes blue
                  - :red[Related] or :red[inverse]: The remaining nodes are labeled as related if the prevalence 
                    of the positive group is larger, or inverse otherwise. Related nodes will be colored orange, and 
                    inverse nodes turquoise
                """
                st.markdown(node_label_msg)

            st.slider(
                'Prevalence thresholds for frequency label', 0.0, 1.0, (0.1, 0.5), key='freq_slider',
                on_change=lambda : freq_handle.set_attr(st.session_state.freq_slider))

            st.slider(
                'Prevalence difference thresholds for distinction label', 0.0, 1.0, (0.1, 0.2),
                help='Only relevant when a positive and negative group are defined', key='prev_diff_slider',
                on_change=lambda : prev_diff_handle.set_attr(st.session_state.prev_diff_slider))
            st.slider(
                'Prevalence ratio thresholds for distinction label', 1.0, 5.0, (1.5, 2.0),
                help='Only relevant when a positive and negative group are defined', key='prev_ratio_slider',
                on_change=lambda : prev_ratio_handle.set_attr(st.session_state.prev_ratio_slider))

            st.subheader('Edge type thresholds')

            if st.checkbox('Show edge type tooltip'):
                edge_type_msg = f"""
                GraphXplore assigns edge types representing the level of conditional relation between two attributes. 
                Edges of higher relation are visualized with the thickest arrow. The following three types are assigned:
                  - :red[High relation]: The conditional increase is at least 
                    :red[{str(st.session_state.cond_increase_thresholds[1])}] or the conditional increase ratio is at 
                    least :red[{str(st.session_state.increase_ratio_thresholds[1])}]
                  - :red[Low relation]: The conditional increase is smaller than 
                    :red[{str(st.session_state.cond_increase_thresholds[0])}] and the conditional increase ratio is 
                    smaller than :red[{str(st.session_state.increase_ratio_thresholds[0])}]
                  - :red[Medium relation]: The remaining edges
                """
                st.markdown(edge_type_msg)

            st.slider(
                'Conditional increase thresholds', 0.0, 1.0, (0.1, 0.2), key='cond_increase_slider',
            on_change=lambda : cond_increase_handle.set_attr(st.session_state.cond_increase_slider))
            st.slider(
                'Conditional increase ratio thresholds', 1.0, 5.0, (1.5, 2.0), key='increase_ratio_slider',
            on_change=lambda : indrease_ratio_handle.set_attr(st.session_state.increase_ratio_slider))


@st.cache_data
def convert_df(dataframe : pd.DataFrame):
    return dataframe.to_csv(index=False).encode('utf-8')

def get_dashboard_select_widget(parent_obj):
    if parent_obj.checkbox('Show dashboard tooltip', key='dashboard_tooltip'):
        """
        Here, you can :red[visually explore] your dataset using a classic :red[dashboard] approach. You can view 
        distributions of single variables (:red[univariate analysis]), or plot the combined distribution of two 
        variables (:red[bivariate analysis]). For both visualizations, you select a :red[table as basis] and add 
        optionally :red[predefined groups]. This way you can compare distributions between groups
        """
    dashboard_meta = VariableHandle(DASHBOARD_META_KEY).get_attr()
    dashboard_lattice_key = 'dashboard_lattice'
    dashboard_lattice = VariableHandle(dashboard_lattice_key).get_attr()
    dashboard_db = VariableHandle(DASHBOARD_DB_KEY).get_attr()
    dashboard_groups = VariableHandle(DASHBOARD_BASIS_GROUPS, init={}).get_attr()
    dashboard_table = VariableHandle(DASHBOARD_BASIS_TABLE).get_attr()
    if dashboard_meta is None:
        parent_obj.info('You need to assign metadata before using the dashboard')
        if main_meta is None:
            parent_obj.info('You need to load/extract/create metadata at "Metadata" in the sidebar. Afterwards, '
                    'you can assign it here')
    else:
        parent_obj.info('Currently assigned metadata has ' + str(len(dashboard_meta.get_table_names()))
                + ' table(s) and ' + str(dashboard_meta.get_total_nof_variables()) + ' variables')

    def assign_dashboard_meta():
        VariableHandle(DASHBOARD_META_KEY).set_attr(copy.deepcopy(main_meta))
        VariableHandle(dashboard_lattice_key).set_attr(MetaLattice.from_meta_data(main_meta))

    st.button('Assign selected metadata', disabled=main_meta is None,
              on_click=assign_dashboard_meta, key='dashboard_meta_assign')

    if dashboard_meta is not None:
        get_database_select_widget(
            parent_obj, DASHBOARD_DB_KEY, 'Select Neo4J base graph database for data retrieval', False, GraphType.Base,
            dashboard_meta)


        if dashboard_db is None:
            parent_obj.info('You have to select a base graph matching the selected metadata as Neo4J database first')
        else:
            parent_obj.success('Base graph "' + dashboard_db + '" selected, and matching metadata assigned')

            with parent_obj.expander('Define visualization basis'):
                whole_table = st.selectbox('Choose table as basis', dashboard_meta.get_table_names())
                all_groups = VariableHandle(DEFINED_GROUP_KEY, init={}).get_attr()
                valid = True
                full_table_group = True
                if len(all_groups) == 0:
                    st.info('No groups defined that could be used for basis of the visualization. If you want to '
                            'define groups, go to "Group Definitions" and load or create groups')
                    chosen_dashboard_groups = {}
                else:
                    group_selection = st.multiselect('Choose groups as basis', all_groups.keys())
                    dashboard_meta_dict = dashboard_meta.to_dict()
                    for group in group_selection:
                        selector_to_check = all_groups[group]
                        if selector_to_check.group_table != whole_table:
                            st.error('Selected group "' + group
                                     + '" does not match selected basis table "' + whole_table + '"')
                            valid = False
                            break
                        if selector_to_check.meta.to_dict() != dashboard_meta_dict:
                            st.error('Group "' + group + '" does not match assigned metadata')
                            valid = False
                            break
                    chosen_dashboard_groups = {group : all_groups[group] for group in group_selection}
                    if len(chosen_dashboard_groups) > 0:
                        full_table_group = st.checkbox('Use all members of basis table as a group', value=True)

                def assign_basis():
                    try:
                        VariableHandle(DASHBOARD_BASIS_TABLE).set_attr(whole_table)
                        VariableHandle(DASHBOARD_BASIS_GROUPS).set_attr(chosen_dashboard_groups)
                        VariableHandle(DASHBOARD_BUILDER).set_attr(DashboardBuilder(
                            dashboard_meta, whole_table, dashboard_db, full_table_group, chosen_dashboard_groups,
                            VariableHandle(NEO4J_ADDRESS_KEY).get_attr(), VariableHandle(NEO4J_AUTH_KEY).get_attr()))
                        VariableHandle(DASHBOARD_FIG).set_attr(None)
                    except AttributeError as err:
                        parent_obj.error('ERROR: ' + str(err))

                st.button('Assign basis', type='primary', disabled=not valid, on_click=assign_basis)

            if dashboard_table is None:
                parent_obj.info('No basis defined yet')
            else:
                dashboard_builder = VariableHandle(DASHBOARD_BUILDER).get_attr()
                basis_msg = 'You chose the following table as basis: "' + dashboard_table + '"'
                if len(dashboard_groups) > 0:
                    basis_msg += ' and the following basis group(s): "' + '", "'.join(dashboard_groups.keys()) + '"'
                parent_obj.success(basis_msg)
                children = set(dashboard_lattice.get_relatives(dashboard_table))
                available_table_vars = collections.defaultdict(list)
                for table in dashboard_meta.get_table_names():
                    if table == dashboard_table or table in children:
                        for var in dashboard_meta.get_variable_names(table):
                            var_info = dashboard_meta.get_variable(table, var)
                            if var_info.variable_type not in [VariableType.PrimaryKey, VariableType.ForeignKey]:
                                available_table_vars[table].append(var)

                one_table = dashboard_meta.get_table_names()[0] if len(dashboard_meta.get_table_names()) == 1 else None
                plot_type_radio_col, plot_type_help_col = parent_obj.columns(2)
                plot_type_select = plot_type_radio_col.radio('Choose type of plot', ['Univariate', 'Bivariate'])
                if plot_type_select == 'Univariate':
                    plot_type_help_msg = """
                    Plot a distribution of a single variable within the basis table and all selected basis groups:
                    - Histograms will be plotted for metric variables
                    - Pie charts for categorical variables
                    """
                    if one_table is not None:
                        uni_table_select = one_table
                        uni_var_select = parent_obj.selectbox('Choose variable for distribution',
                                                               available_table_vars[uni_table_select])
                    else:
                        table_col, var_col = parent_obj.columns(2)
                        uni_table_select = table_col.selectbox('Choose table of variable', available_table_vars.keys())
                        uni_var_select = var_col.selectbox('Choose variable for distribution',
                                                            available_table_vars[uni_table_select])

                    uni_var_info = dashboard_meta.get_variable(uni_table_select, uni_var_select)

                    if uni_var_info.variable_type == VariableType.Metric:
                        y_scale_select = parent_obj.radio('Choose y-scale type', ['Member Count', 'Member Fraction'])
                        y_scale_type = HistogramYScaleType.Count if y_scale_select == 'Member Count' else HistogramYScaleType.Fraction
                    else:

                        y_scale_type = None

                    query_func = dashboard_builder.get_variable_dist_plot
                    args = [uni_table_select, uni_var_select, y_scale_type]

                else:
                    plot_type_help_msg = """
                    Plot the combined distribution of two variables within the basis table and all selected basis groups:
                    - Scatter plots will be used for pairs of metric variables
                    - Multiple box plots will used for pairs of metric and categorical variables
                    - Stacked bar charts will be used for paris of categorical variables
                    """
                    if one_table is not None:
                        bi_first_table_select, bi_second_table_select = one_table, one_table
                        first_var_col, second_var_col = parent_obj.columns(2)
                        bi_first_var_select = first_var_col.selectbox('Choose first variable for correlation',
                                                                        available_table_vars[bi_first_table_select])
                        bi_second_var_select = second_var_col.selectbox('Choose second variable for correlation',
                                                                          [var for var in
                                                                           available_table_vars[bi_second_table_select]
                                                                           if
                                                                           var != bi_first_var_select])
                    else:
                        first_table_col, first_var_col, second_table_col, second_var_col = parent_obj.columns(4)
                        bi_first_table_select = first_table_col.selectbox('Choose table of first variable',
                                                                            available_table_vars.keys())
                        bi_first_var_select = first_var_col.selectbox('Choose first variable for distribution',
                                                                        available_table_vars[bi_first_table_select])
                        bi_second_table_select = second_table_col.selectbox('Choose table of second variable',
                                                                              available_table_vars.keys())
                        second_vars_to_choose = (available_table_vars[bi_second_table_select]
                                                 if bi_first_table_select != bi_second_table_select
                                                 else [var for var
                                                       in dashboard_meta.get_variable_names(bi_second_table_select)
                                                       if var != bi_first_var_select])
                        bi_second_var_select = second_var_col.selectbox('Choose second variable for distribution',
                                                                          second_vars_to_choose)
                    query_func = dashboard_builder.get_correlation_plot
                    args = [bi_first_table_select, bi_first_var_select, bi_second_table_select,
                            bi_second_var_select]

                plot_type_help_col.markdown(plot_type_help_msg)

                def query_plot():
                    try:
                        fig = query_func(*args)
                        VariableHandle(DASHBOARD_FIG).set_attr(fig)
                        curr_task = VariableHandle(CURR_TASK).get_attr()
                        if curr_task is not None and isinstance(curr_task,
                                                                TriggerProcess) and curr_task.goal == WorkflowGoal.ExploreDashboard:
                            curr_task.done_triggered = True
                    except AttributeError as err:
                        parent_obj.error('ERROR: ' + str(err))

                parent_obj.button('Query data for visualization', type='primary', on_click=query_plot)

                dashboard_fig = VariableHandle(DASHBOARD_FIG).get_attr()
                if dashboard_fig is not None:
                    parent_obj.plotly_chart(dashboard_fig, use_container_width=True)

def add_group_to_selection(group_to_add : str):
    agg_meta_dict = VariableHandle(AAG_META_KEY).get_attr().to_dict()
    all_defined_groups = VariableHandle(DEFINED_GROUP_KEY).get_attr()
    selector_to_check = all_defined_groups[group_to_add]
    group_valid = True
    if len(all_defined_groups) > 0:
        first_group, first_selector = next(iter(all_defined_groups.items()))
        if selector_to_check.group_table != first_selector.group_table:
            st.error('Chosen group "' + group_to_add
                     + '" is based on table "' + selector_to_check.group_table
                     + '". However this does not match the table "'
                     + first_selector.group_table + '" of already selected group "'
                     + first_group + '"')
            group_valid = False
    if selector_to_check.meta.to_dict() != agg_meta_dict:
        st.error('Group "' + group_to_add + '" does not match assigned metadata')
        group_valid = False
    if group_valid:
        VariableHandle(AAG_CHOSEN_GROUPS).get_attr()[group_to_add] = selector_to_check

def delete_group_and_reset_dist(group_to_del : str):
    del VariableHandle(AAG_CHOSEN_GROUPS).get_attr()[group_to_del]
    for group_key in [AAG_POS_GROUP, AAG_NEG_GROUP]:
        dist_group = VariableHandle(group_key).get_attr()
        if dist_group is not None and dist_group == group_to_del:
            VariableHandle(group_key).set_attr(None)

def set_group_dist(group_to_set: str, set_pos_group: bool):
    for group_key in [AAG_POS_GROUP, AAG_NEG_GROUP]:
        dist_group = VariableHandle(group_key).get_attr()
        if dist_group is not None and dist_group == group_to_set:
            VariableHandle(group_key).set_attr(None)
    VariableHandle(AAG_POS_GROUP if set_pos_group else AAG_NEG_GROUP).set_attr(group_to_set)

def translate_data_to_graph(parent_obj, meta_key: str, data_key: str, missing_vals_key, db_name_key, overwrite: bool):
    try:
        curr_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
        curr_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
        translator = GraphTranslator(st.session_state[meta_key], tuple(st.session_state[missing_vals_key]))
        translator.transform_to_graph(st.session_state[data_key], st.session_state[db_name_key],
                                      GraphOutputType.Database, overwrite, curr_address, curr_auth)
        refresh_existing_databases()
        parent_obj.success('Converted data to a graph and stored it in "' + st.session_state[db_name_key] + '"')
        curr_task = VariableHandle(CURR_TASK).get_attr()
        if curr_task is not None and isinstance(curr_task,
                                                TriggerProcess) and curr_task.goal == WorkflowGoal.CreateBaseGraph:
            curr_task.done_triggered = True
    except AttributeError as error:
        parent_obj.error('ERROR: ' + str(error))

def generate_aag_graph(parent_obj, overwrite: bool):
    try:
        curr_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
        curr_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
        groups_for_aag = VariableHandle(AAG_CHOSEN_GROUPS).get_attr()
        out_db = VariableHandle(AGG_RESULT_DB_KEY).get_attr()
        generator = AttributeAssociationGraphGenerator(
            db_name=VariableHandle(AAG_INPUT_DB_KEY).get_attr(),
            group_selection=groups_for_aag,
            positive_group=VariableHandle(AAG_POS_GROUP).get_attr(),
            negative_group=VariableHandle(AAG_NEG_GROUP).get_attr(),
            pre_filter=st.session_state.pre_filter, post_filter=st.session_state.post_filter,
            frequency_thresholds=st.session_state.freq_thresholds,
            prevalence_diff_thresholds=st.session_state.prevalence_diff_thresholds,
            prevalence_ratio_thresholds=st.session_state.prevalence_ratio_thresholds,
            cond_increase_thresholds=st.session_state.cond_increase_thresholds,
            increase_ratio_thresholds=st.session_state.increase_ratio_thresholds,
            address=curr_address,
            auth=curr_auth)
        attribute_assoc_graph = generator.generate_graph()
        GraphDatabaseWriter.write_graph(db_name=out_db,
                                        graph=attribute_assoc_graph, overwrite=overwrite,
                                        address=curr_address, auth=curr_auth)
        refresh_existing_databases()
        parent_obj.success('Generated attribute association graph and stored it in database "' + out_db + '"')
        curr_task = VariableHandle(CURR_TASK).get_attr()
        if curr_task is not None and isinstance(curr_task, TriggerProcess) and curr_task.goal == WorkflowGoal.CreateAAG:
            curr_task.done_triggered = True
    except AttributeError as exc:
        parent_obj.error('ERROR: ' + str(exc))

def query_aag_for_table(parent_obj, table_query: str):
    try:
        curr_aag_table_db = VariableHandle(AAG_TABLE_DB_KEY).get_attr()
        curr_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
        curr_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
        table_records = GraphDatabaseUtils.execute_query(
            query=table_query, database=curr_aag_table_db,
            address=curr_address, auth=curr_auth)
        if len(table_records) == 0:
            raise AttributeError('Could not retrieve any data')
        extracted_groups = []
        extracted_group_msgs = []
        data = []
        for row_dict in table_records:
            try:
                if extracted_groups is not None and len(extracted_groups) == 0:
                    groups, group_size, positive_group, negative_group = BaseUtils.extract_group_info_from_list(
                        row_dict['groups'])
                    extracted_groups = groups
                    for group in groups:
                        group_msg = f"""
                        #### {group}
                        Group size: {str(group_size[group])}  
                        {':red[Positive group]' if positive_group is not None and positive_group == group
                        else ':blue[Negative group]' if negative_group is not None and negative_group == group else ''}
                        """
                        extracted_group_msgs.append(group_msg)
                    VariableHandle(AGG_TABLE_GROUPS_KEY).set_attr(extracted_group_msgs)
            except AttributeError as e:
                print(e)
                extracted_groups = None

            data_row = {}

            if extracted_groups is None:
                extracted_groups = row_dict['groups']

            for key, val in row_dict.items():
                if key in ['agg', 'groups']:
                    continue
                if 'refRange' in key:
                    if val is None:
                        data_row[key] = (None, None)
                    else:
                        data_row[key] = tuple(val)
                elif isinstance(val, list):
                    for val_idx in range(len(val)):
                        data_row[key + '_' + extracted_groups[val_idx]] = val[val_idx]
                elif 'value' in key:
                    data_row[key] = str(val)
                else:
                    data_row[key] = val

            data.append(data_row)
        df = pd.DataFrame(data)
        VariableHandle(AAG_TABLE_RESULT_KEY).set_attr(df)
        curr_task = VariableHandle(CURR_TASK).get_attr()
        if curr_task is not None and isinstance(curr_task, TriggerProcess) and curr_task.goal == WorkflowGoal.ExploreAAG:
            curr_task.done_triggered = True
    except AttributeError as neo4j_error:
        parent_obj.error('ERROR:' + str(neo4j_error))


def load_groups(parent_obj, loaded_group_bytes, file_encoding: str):
    if loaded_group_bytes is not None:
        try:
            if file_encoding == 'auto':
                enc = chardet.detect(loaded_group_bytes.getvalue())['encoding']
                # ascii (without special characters) is subset of utf-8
                if enc == 'ascii' or enc == 'utf-8':
                    enc = 'utf-8-sig'
            else:
                enc = file_encoding
            input_dict = json.loads(loaded_group_bytes.getvalue().decode(enc))
            if 'defined_groups' not in input_dict:
                raise AttributeError('Group JSON must contain an entry "defined_groups" will all predefined groups as a list')
            curr_groups = VariableHandle(DEFINED_GROUP_KEY).get_attr()
            meta = VariableHandle(GROUP_LOAD_META).get_attr()
            overwritten_groups = []
            for group_dict in input_dict['defined_groups']:
                if 'group_name' not in group_dict:
                    raise AttributeError('Dict for group must contain an entry "group_name" with the name of the group')
                new_group_name = group_dict['group_name']
                if 'group_table' not in group_dict:
                    raise AttributeError('Dict for group must contain an entry "group_table" with the table of the '
                                         'group members')
                new_group_table = group_dict['group_table']
                if 'condition' not in group_dict:
                    raise AttributeError('Dict for group must contain an entry "condition" with the logical filter '
                                         'expression')
                new_condition = LogicOperatorParser.from_string(group_dict['condition'])
                if new_group_table in curr_groups:
                    overwritten_groups.append(new_group_table)
                curr_groups[new_group_name] = GroupSelector(new_group_table, meta, new_condition)
            parent_obj.success('Loaded predefined groups')
            if len(overwritten_groups) > 0:
                parent_obj.warning('The definition of the following group(s) were overwritten: "'
                                   + '", "'.join(overwritten_groups) + '"')
            curr_task = VariableHandle(CURR_TASK).get_attr()
            if curr_task is not None and isinstance(curr_task, LoadGroups):
                curr_task.done_triggered = True
        except AttributeError as e:
            parent_obj.error('ERROR: ' + str(e))
    else:
        parent_obj.error('ERROR: You have to select a file')

def assign_neo4j_browser_styling():
    with open(BROWSER_STYLE_PATH) as style_file:
        to_add = ''.join(style_file.readlines()) + '\n'
        new_file_str = ''
        curr_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
        curr_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
        all_labels = set()
        for db in VariableHandle(EXISTING_DATABASES_KEY).get_attr():
            labels = GraphDatabaseUtils.execute_query('call db.labels()', db, curr_address, curr_auth)
            all_labels.update((entry['label'] for entry in labels))
        for label in all_labels:
            if (label in BaseNodeType._value2member_map_
                    or label in FrequencyLabel._value2member_map_
                    or label in DistinctionLabel._value2member_map_):
                continue
            new_file_str += 'node.' + label + ' {\n  defaultCaption: "<id>";\n}\n'
        new_file_str += to_add
        st.session_state.desktop_style = new_file_str.encode()



if __name__ == '__main__':
    st.set_page_config(page_title='Data Exploration', page_icon=ICON_PATH)
    st.title('Data Exploration')
    workflow = Workflow()
    workflow.render()
    neo4j_address = VariableHandle(NEO4J_ADDRESS_KEY).get_attr()
    neo4j_auth = VariableHandle(NEO4J_AUTH_KEY).get_attr()
    main_meta = VariableHandle(MAIN_META_KEY).get_attr()
    get_neo4j_connection_widget(st)
    if neo4j_address is None or neo4j_auth is None:
        connection_msg = """
        You have to start a Neo4J database management system and assign a connection to it before starting with the 
        data exploration
        """
        st.info(connection_msg)
    else:
        st.info('Neo4J DBMS connection assigned at address "' + neo4j_address
                + '". Keep this connection available during your whole exploration workflow or change it accordingly')
        generation_tab, exploration_tab, group_tab = st.tabs(['Graph Generation', 'Data Exploration', 'Group Definitions'])
        with generation_tab:
            base_graph_gen_tab, aag_gen_tab = st.tabs(['Base Graph Generation', 'Attribute Association Graph Generation'])
            with base_graph_gen_tab:
                if st.checkbox('Show base graph tooltip'):
                    """
                    Most often data is presented in relational form as a collection of tables. Assuming each table has 
                    a variable functioning as primary key, a single row of a table represents the attributes assigned 
                    to its primary key value. E.g., the primary key could be a patient ID in a hospital information 
                    system, and the other variables could contain diagnoses or measurements such as heart rate, 
                    laboratory results, etc.\n  
                    Here, this relational view of data is translated to a graph-based representation which is called a 
                    :red[base graph] as it forms the basis of all data exploration in GraphXplore. Firstly, the 
                    values of all variables of a table are deduplicated to :red[form unique triples of table, variable 
                    name and cell value as nodes]. Secondly, an :red[edge] is formed :red[between the node for a 
                    primary key value and the nodes of all triples existing in its table row]. Optionally, :red[metric 
                    variable values are binned if specified] this way in the metadata. An 
                    additional node is created for each bin of the variable and connected by an edge to each node 
                    assigned to that bin. The resulting graph is stored as a Neo4J database. This has several 
                    advantages:
                    * Relationships between variables of different tables due to foreign key relations are intuitively 
                    represented by paths in the graph
                    * Queries (especially queries across different tables like an SQL-join) can be executed very 
                    efficiently, 
                    since the edges of the graph function similarly to a database index
                    * The data can be visually explored in the Neo4J Browser and queried intuitively using the Neo4j 
                    Cypher query language
                    """
                translation_meta = VariableHandle(TRANSLATION_META_KEY).get_attr()
                translation_db = VariableHandle(TRANSLATION_DB_KEY).get_attr()
                meta_msg_container = st.container()
                st.button('Assign metadata', type='primary', key='metadata_assign_translation',
                          disabled=main_meta is None,
                          help='disabled until metadata was selected' if main_meta is None else None,
                          on_click=lambda : VariableHandle(TRANSLATION_META_KEY).set_attr(copy.deepcopy(main_meta)))
                if translation_meta is None:
                    meta_msg_container.info(
                        'Metadata of the relational dataset not yet assigned. You can use the tab "Meta Data" to '
                        'load/extract/create a metadata object and afterwards assign it here')
                else:
                    meta_msg_container.success(
                        'Metadata contains ' + str(len(translation_meta.get_table_names()))
                        + ' table(s) and ' + str(translation_meta.get_total_nof_variables()) + ' variables')

                    missing_vals_list = EditableList(
                        'translation_missing_vals', ['', 'NaN', 'Na', 'NA', 'NAN', 'nan', 'na'],
                        list_help='These values are considered as synonyms for unfilled data and are excluded from the '
                                  'base graph generation. The rest of the table row will still be converted')
                    missing_vals_list.render(base_graph_gen_tab.expander('Missing values'))

                    extract_data_uploader = CSVUploader(TRANSLATION_SOURCE_DATA_KEY,
                                                        'Choose CSV files for translation to base graph',
                                                        required_tables=translation_meta.get_table_names())
                    extract_data_uploader.render()
                    trans_source_data = VariableHandle(TRANSLATION_SOURCE_DATA_KEY).get_attr()
                    if len(trans_source_data) > 0:
                        st.success('Uploaded table(s): "' + '", "'.join(trans_source_data.keys()) + '"')
                    else:
                        st.info('No CSV tables uploaded yet')

                    trans_overwrite = get_database_select_widget(base_graph_gen_tab, TRANSLATION_DB_KEY,
                                                                 'Select Neo4J database for storage', True)

                    ready_for_translation = (translation_meta is not None
                                             and len(trans_source_data) > 0
                                             and translation_db is not None)
                    st.button('Start graph generation', type='primary', disabled=not ready_for_translation,
                              help=None if ready_for_translation else 'Metadata must be assigned, CSV files must be uploaded, '
                                                                      'and Neo4j database must be specified',
                              on_click=translate_data_to_graph, args=[
                            base_graph_gen_tab, TRANSLATION_META_KEY, TRANSLATION_SOURCE_DATA_KEY,
                            'translation_missing_vals', TRANSLATION_DB_KEY, trans_overwrite
                        ])

            with aag_gen_tab:
                aag_meta = VariableHandle(AAG_META_KEY).get_attr()
                aag_input_db = VariableHandle(AAG_INPUT_DB_KEY).get_attr()
                aag_groups = VariableHandle(AAG_CHOSEN_GROUPS, init={}).get_attr()
                aag_result_db = VariableHandle(AGG_RESULT_DB_KEY).get_attr()
                if st.checkbox('Show attribute association graph tooltip'):
                    """
                    Attribute association graphs can be used for an intuitive visual exploration of your data. You 
                    start with a base graph database and a selection of primary key groups (e.g. patient IDs of 
                    patients with a certain condition). GraphXplore analyses statistical distributions of 
                    all attributes (a single value of a variable) which exist for these groups in the dataset (in the 
                    origin table and all foreign tables). The results are stored as nodes in the graph with one node 
                    for each unique attribute and absolute count as well as prevalence (accounting for missing values) 
                    of this attribute in each group selected by you. Differences in prevalence between groups are 
                    calculated in absolute and relative form. Additionally, relations between attributes are derived 
                    and represented by edges in the graph. Absolute co-occurrences and conditional prevalence are 
                    calculated and compared with unconditional prevalence of the attributes. The nodes and edges of the 
                    graph are labeled an visually highlighted based on their statistical traits. This way, GraphXplore 
                    guides you during your data exploration. You can define custom filters for the attributes to 
                    consider and how the graph will be labeled in the *Advanced options* section below. For further 
                    information, how to start the exploration and detailed description of all metrics please check out 
                    the user guide.
                    """

                if aag_meta is None:
                    st.info('You need to assign metadata before generating an attribute association graph from it')
                    if main_meta is None:
                        st.info(
                            'You need to load/extract/create metadata at "Metadata" in the sidebar. Afterwards, '
                            'you can assign it here')
                else:
                    st.info('Currently assigned metadata has ' + str(len(aag_meta.get_table_names()))
                                    + ' table(s) and ' + str(aag_meta.get_total_nof_variables()) + ' variables')

                cont = st.container()

                cont.button(
                    'Assign selected metadata', disabled=main_meta is None, on_click=FunctionWrapper.wrap_func,
                    args=[cont, 'Metadata assigned', VariableHandle(AAG_META_KEY).set_attr, copy.deepcopy(main_meta)],
                    key='agg_meta_assign')

                if aag_meta is not None:
                    get_database_select_widget(
                        cont, AAG_INPUT_DB_KEY, 'Select Neo4J base graph database', False, GraphType.Base, aag_meta)

                    if aag_input_db is None:
                        st.info(
                            'You have to select a base graph matching the selected metadata as Neo4J database first')
                    else:
                        st.success('Input base graph "' + aag_input_db + '" selected, and matching metadata assigned')

                        pos_group = VariableHandle(AAG_POS_GROUP).get_attr()
                        neg_group = VariableHandle(AAG_NEG_GROUP).get_attr()

                        with st.expander('Group selection'):
                            st.subheader('Selected groups')
                            if len(aag_groups) == 0:
                                st.info('No groups selected yet')
                            else:
                                for group_name, selector in aag_groups.items():
                                    st.markdown('**Group name**: ' + group_name)
                                    st.markdown('**Group table**: ' + selector.group_table)
                                    st.markdown('**Group condition**: ' + str(selector.group_filter))
                                    st.button('Deselect group', key='del_group_' + group_name,
                                              on_click=delete_group_and_reset_dist,
                                              args=[group_name])
                                    if pos_group is not None and pos_group == group_name:
                                        st.markdown(':red[Positive group]')
                                    if neg_group is not None and neg_group == group_name:
                                        st.markdown(':blue[Negative group]')
                                    st.divider()

                            st.subheader('Add groups to selection')

                            all_groups = VariableHandle(DEFINED_GROUP_KEY, init={}).get_attr()
                            if len(all_groups) == 0:
                                st.info(
                                    'No groups defined that could be selected here. If you want to '
                                    'define groups, go to "Group Definitions" and load or create groups')
                            else:
                                group_add_options = [entry for entry in all_groups.keys() if entry not in aag_groups]
                                if len(group_add_options) == 0:
                                    st.info('You already selected all defined groups. If you want to '
                                    'define new groups, go to "Group Definitions" and load or create groups')
                                else:
                                    group_selection = st.selectbox(
                                        'Choose group to add',
                                        group_add_options)
                                    st.button('Add group', type='primary', on_click=add_group_to_selection,
                                              args=[group_selection])

                            st.subheader('Assign group distinction')
                            if st.checkbox('Show group distinction tooltip'):
                                """
                                In the attribute association graph, the distinction of attribute prevalence between groups
                                can be identified and attributes with a high distinction will be highlighted. For this
                                distinction you have to assign a :red[positive] and a :blue[negative] group. Attributes
                                which appear more often in the positive group (compared to the negative group) will be
                                labeled as "highly related" or "related" and displayed in red or orange. Conversely,
                                attributes which appear more often in the negative group will be labeled as
                                "highly inverse" or "inverse" and displayed in blue or turquoise. This can help you in
                                identifying attributes of interest during you data exploration.
                                """
                            if len(aag_groups) == 0:
                                st.info('You have to select groups before assigning their distinction')
                            else:
                                dist_group_type_col, dist_group_select_col = st.columns(2)
                                group_type = dist_group_type_col.radio('Select group type to assign',
                                                                       ['Positive', 'Negative'])
                                dist_group_name = dist_group_select_col.selectbox(
                                    'Choose group to assign', aag_groups.keys())
                                st.button('Assign group', type='primary', on_click=set_group_dist,
                                          args=[dist_group_name, group_type == 'Positive'])

                        get_generator_advanced_options_widget(aag_gen_tab)

                        aag_overwrite = get_database_select_widget(aag_gen_tab, AGG_RESULT_DB_KEY,
                                                                   'Select Neo4J database for storage of the attribute '
                                                                   'association graph', True)
                        st.button(
                            'Start graph generation', type='primary', on_click=generate_aag_graph,
                            args=[aag_gen_tab, aag_overwrite], disabled=aag_result_db is None or len(aag_groups) == 0,
                            help='You have to define at least one group and select a database for storage of the results')


        with exploration_tab:
            aag_explain_tab, aag_tabular_tab, dashboard_tab = st.tabs(
                ['Intro to Attribute Association Graphs', 'Attribute Association Graph Tabular View',
                 'Dataset Dashboard'])

            with aag_explain_tab:
                metrics_tab, neo4j_tab = st.tabs(['Properties', 'Neo4J Quick Start and Configuration'])
                with metrics_tab:
                    msg = """
                    ### Use case
                    Attribute association graphs (AAG) are meant to support you during your data exploration with visual 
                    highlights of various forms. Note that AAGs capture very basic statistical parameters that are 
                    intuitive and applicable to any dataset. While this form of data exploration is very accessible 
                    and can help you to familiarize yourself with your dataset or formulate hypothesis, it does not 
                    replace thorough statistical inference which should be the next step in your data analysis.
                    
                    ### What is a graph?
                    A graph in general consists of *nodes* which can represent arbitrary objects and *edges* (also 
                    called *relationships*) which point from a source node to a target node and describe some 
                    association between the objects represented by the source and target node. A good example could be 
                    a set of research articles which are represented as nodes, and edges pointing from one article to 
                    another article that is cited in the first one. In the visualization of a graph, nodes are 
                    depicted as circles (or points) and edges as arrows pointing from the source node circle to the 
                    target node circle. This form of visualization allows to encode different traits of the nodes and 
                    edges via colors, size of circles, thickness of arrows, and visual clustering.
                    
                    ### Data Groups
                    During the generation of an AAG one or multiple groups of primary keys are defined. This could for 
                    example be disease and control cohorts as they are used in case-control studies, patients with 
                    different procedures during their hospital stay, or simply all primary keys. GraphXplore 
                    measures several statistical traits within these groups and their difference (if multiple groups 
                    were defined). Optionally, some groups can be defined as *positive* or *negative* which will affect 
                    the parameters and visualization of nodes. This will be explained in later paragraphs.
                    
                    ### AAG Overview
                    Each node of an AAG represents a so-called *attribute* being a unique variable value. Since 
                    attributes are unique, two primary keys (e.g. two patients) can share the same attribute (e.g. a 
                    diagnosis or age group). Nodes describe several statistical metrics about the occurrence of its 
                    attribute within the selected groups and the difference between group occurrences. In the 
                    visualization, the attributes are represented as the node's circles and its statistical parameters 
                    are encoded via size and color.  
                    
                    The edges of an AAG capture conditional relationships between attributes. Conditional relationships 
                    describe how the presence of one attribute influences the presence of another attribute. Does the 
                    likelihood increase? How does this increase (or decrease) differ between groups? E.g. how does 
                    reduced renal function affect hemoglobin levels? How does this dependency differ between patients 
                    with and without hypertension? Compared to nodes capturing information about a single attribute, 
                    edges might be a little bit harder to comprehend since the added condition also adds another layer 
                    of complexity. Feel free to revisit this introduction multiple times until you feel familiar with 
                    its concepts. Edges are visualized as arrows where the arrow thickness encodes the strength of the 
                    conditional relationship. Additionally, attributes which are either connected directly by an edge, 
                    or share a common connected attribute, tend to cluster in the visualization. As a result, groups of 
                    attributes which have some level of conditional relationship can be explored in the same area of 
                    the graph visualization.
                    
                    ### How to explore AAGs?
                    
                    Here, We will talk about how to *interpret* the AAG visualization and how it can help you during 
                    your data exploration. If you want to know you to operate Neo4J, check out the other tab "Neo4J 
                    Quick Start and Configuration". If you want to learn, what the nodes and edges encode in detail, 
                    click on the drop-downs below.
                    """
                    st.markdown(msg)

                    st.image(get_how_to_image_path('aag_overview'))

                    msg = """
                    Above you can see a birdseye view of an AAG in Neo4J Bloom as a screenshot. You can see that there 
                    are a lot of red and orange nodes in the center with a lot of connections between them. These 
                    represent attributes statistically related to the positive group (e.g. disease cohort). As they are 
                    clustered together, they might have some conditional dependencies. On the outer parts of the 
                    screenshot you can see blue and turquoise nodes in at least two clusters which are statistically 
                    related to the negative group (e.g. control cohort). Lastly, there are beige nodes throughout the 
                    screenshot which have roughly similar statistical properties in the positive and negative group and 
                    thus could be of less interest in the initial exploration. It might be a good idea to start with a 
                    cluster of nodes with a dark color (red or blue) and zoom in.
                    """

                    st.markdown(msg)

                    st.image(get_how_to_image_path('aag_detailed'))

                    msg = """
                    Above you can see an example how a few nodes and their edges might look like, e.g. once you zoomed 
                    in from the birdseye view. The variable name of the attribute is shown in bold in the circle of the 
                    nodes followed by the value. The size of the nodes indicates how frequently this attribute occurs. 
                    The beige and red nodes occur very 
                    frequently, the turquoise and blue nodes frequently, and the orange node infrequently. You might 
                    want to check out the red node first, as its attribute occurs frequently and is statistically 
                    related to the positive group. Additionally, it is connected by edges to the orange and beige node.   
                    The red and orange node share two edges (conditional dependency in both directions), however one of 
                    these marks a "high impact relation", the other a "medium impact relation". This could be 
                    interesting to explore. You can double-click on the nodes and edges to inspect them in more detail. 
                    Regarding the blue node, it might be interesting to find out why it has no edge (i.e. no measured 
                    conditional dependency) although it is statistically related to the negative group. To summarize,
                    you might want to explore visual clusters, strongly colored nodes, absence of edges, and of course 
                    the statistical parameter which are explained in detail in the drop-downs.
                    """

                    st.markdown(msg)


                    with st.expander('#### Nodes in More Detail'):
                        node_msg = """
                        Nodes describe information about a single attribute and its distribution across different groups. 
                        General information about the attribute and its statistical traits are captured as *parameters*.
                        
                        #### Node Parameters
                        The node parameters of an AAG can be split into general information and statistical parameters.
                        
                        ##### General Attribute Information
                        
                        | Parameter | Description | Datatype | Example |
                        | --- | --- | --- | --- |
                        | name | The variable name | string | SysBloodPressure |
                        | value | The unique variable value | string, integer or decimal | high |
                        | description | A short text describing the meaning of the variable, or adding context such as a unit of measurement. This parameter is optional and can be set during the metadata editing | string | sitting, mmHg |
                        | refRange | The reference range for "normal" values of a binned metric variable. This parameter only exists, when the variable was binned during translation to a base graph. This reference range was either set manually during metadata editing, or calculated by GraphXplore to include the middle 60% of values. All values above this reference range are considered "high", and below as "low" | list of two integers or decimals | [0,120] |
                        | groups | A list of all group names together with their number of members. The order of group names gives the order of statistical metrics which are lists. If the positive and negative group were set during AAG creation, these groups have a "[+]" and "[-]" at the end of their string | list of strings | ["disease (100)[+]", "control (900)[-]"] |
                        
                        All general attribute information (apart from the "group" parameter) is taken directly from the 
                        base graph that was generated when translating your relational dataset to a graph form.
                        
                        ##### Statistical Attribute Metrics
                        
                        For the formulas, let $g_1,\dots,g_n$ be the number of group members, and $a_1,\dots,a_n$ be the 
                        number of group members having a valid (i.e. not a missing) value for this attribute.
                        
                        | Parameter | Description | Datatype | Formula | Example |
                        | --- | --- | --- | --- | --- |
                        | count | The number of members of each group having this attribute | list of non-negative integers | $c_i$ | [80, 445] |
                        | missing | The ratio of members of each group having a missing value (e.g. a contaminated blood sample or invalid measurement) for this attribute's variable. If this ratio is high (e.g. between 0.5 and 1.0), the expressiveness of the other statistical metrics could be limited | list of decimals between 0.0 and 1.0 | ${1 - \\dfrac{a_i}{g_i}}$ | [0.0, 0.1] |
                        | prevalence | The ratio of members of each group having this attribute. Group members with missing values are excluded. High values might indicate that this attribute is frequently observed within the group | list of decimals between 0.0 and 1.0 | ${p_i = \\dfrac{c_i}{a_i}}$ | [0.8, 0.5] |
                        | prevalence_difference | The absolute difference between group prevalence, also know as risk difference. If positive and negative group are set, the prevalence difference between these two groups is calculated. If they are not set, the maximum absolute pairwise prevalence difference is calculated. If only one group exists, this parameter will be empty. A high difference might indicate a potentially high specificity of the attribute for a group | decimal between 0.0 and 1.0 | $\\vert p_i - p_j\\vert$ | 0.3 |
                        | prevalence_ratio | The ratio of group prevalence, also known as the risk ratio. If positive and negative group are set, the prevalence ratio is calculated as the larger prevalence divived be the smaller (or equal) prevalence of these two. If they are not set, the overall maximum prevalence is divided by the overall minimum prevalence. If only one group exists, this parameter will be empty. A high ratio might indicate a potentially high sensitivity of the attribute for a group | decimal greater or equal to 1.0 | $\\dfrac{max(p_i)}{min(p_i)}$ | 1.6 | 
                        
                        #### Visual Node Appearance and Labels
                        
                        The visualization of nodes is used to encode some of its statistical attribute parameters. For 
                        this, the *color* and *size* of its circle are adjusted. Additionally, the same information is encoded 
                        in the node labels. The thresholds used below are only the default values and can be adjusted 
                        during AAG creation.
                        - The *size* captures the frequency of its attribute which GraphXplore defines as the maximum group 
                          prevalence $p$:
                            - $p \geq 0.5$: The node is labeled as *highly frequent* and depicted with the largest circle
                            - $0.1 \leq p < 0.5$: The node is labeled as *frequent* and depicted with a medium-sized circle
                            - $p < 0.1$: The node is labeled as *infrequent* and depicted with the smallest circle
                        - The *color* captures the distinction of the attribute between the positive and negative group. 
                        As a result, the coloring is only used when the AAG has defined positive and negative group. 
                        GraphXplore uses the prevalence difference $d$ and prevalence ratio $r$ for the distinction:
                            - $d \geq 0.2$ or $r \geq 2.0$: The node is labeled as *highly related* and colored in red, if 
                              the positive group prevalence as larger, or labeled as *highly inverse* and colored in blue, 
                              if the negative group prevalence is larger
                            - $d < 0.2$ and $r < 2.0$ and ($d \geq 0.1$ or $r \geq 1.5$): The node is labeled as *related* 
                              and colored in orange if  the positive group prevalence as larger, or labeled as *inverse* 
                              and colored in turquoise, if the negative group prevalence is larger
                            - $d < 0.1$ and $r < 1.5$: The node is labeled as *unrelated* and colored in beige
                        """
                        st.markdown(node_msg)
                    with st.expander('#### Edges in More Detail'):
                        edge_msg = """
                        The edges of an AAG capture conditional relationships between attributes. For the rest of this 
                        section lets consider the conditional relationship of an attribute $y$ to the 
                        presence of an attribute $x$. The corresponding edge in the AAG would point from the node for 
                        attribute $x$ to the node for attribute $y$.
                        
                        #### Edge Parameters
                        
                        For the formulas, let $c_{x_1},\dots,c_{x_n}$ be the count of attribute $x$ in the different 
                        groups, and $p_{y_1},\dots,p_{y_n}$ be the prevalence of $y$ in the different groups.
                        
                        | Parameter | Description | Datatype | Formula | Example |
                        | --- | --- | --- | --- | --- |
                        | groups | A list of all group names together with their number of members, same as the node parameter "groups". The order of group names gives the order of statistical metrics which are lists. If the positive and negative group were set during AAG creation, these groups have a "[+]" and "[-]" at the end of their string | list of strings | | ["disease (100)[+]", "control (900)[-]"] |
                        | co_occurrence | The number of members of each group have both attributes $x$ and $y$ | list of integers | $o_i$ | [50, 600] |
                        | conditional_prevalence | The ratio of members of each group with the presence of attribute $x$ that also have attribute $y$. This is the empirical version of the conditional probability $P(y \\vert x)$ | list of decimals between 0.0 and 1.0 | ${\\~{p_i} = \\dfrac{o_i}{c_{x_i}}}$ | [0.625, 0.75] |
                        | conditional_increase | The difference between the conditional prevalence of $y$ given $x$ and the (unconditional) prevalence of $y$ for each group. If the conditional prevalence is smaller than the unconditional one, this value will be negative showing a conditional decrease | list if decimals between -1.0 and 1.0 | ${\\~{p_i} - p_{y_i}}$ | [0.125, -0.15] |
                        | increase_ratio | The ratio of the conditional prevalence of $y$ given $x$ and the (unconditional) prevalence of $y$ for each group. If this ratio is smaller than 1.0 it marks a conditional decrease | list of positive decimals | $\\dfrac{\\~{p_i}}{p_{y_i}}$ | [1.25, 0.833] |
                        
                        #### Visual Edge Appearance
                        
                        Edges are depicted as arrows. The *thickness* of edges is used to depict the strength of the 
                        conditional relationship. The same information is encoded in the edge type. Additionally, 
                        attributes which share an edge tend to be visualized close together. As a result, groups of 
                        attributes which have some level of conditional relationship with each other tend to cluster in the 
                        visualization. GraphXplore measures the strength of a conditional relationship by its largest 
                        conditional increase $i$ and the largest conditional increase ratio $r_i$ across groups. The 
                        thresholds used below are only the default values and can be adjusted during AAG creation.
                        - $i \geq 0.2$ or $r_i \geq 2.0$: The edge type *high relation* is assigned and the arrow is 
                          depicted with the greatest thickness
                        - $i < 0.2$ and $r_i < 2.0$ and ($i \geq 0.1$ or $r_i \geq 1.5$): The edge type *medium relation* 
                          is assigned and the arrow is depicted with a medium thickness
                        - $i < 0.1$ and $r_i < 1.5$: The edge type *low relation* is assigned and the arrow is depicted 
                          with the smallest thickness
                        """
                        st.markdown(edge_msg)
                with neo4j_tab:
                    msg = """
                    ### Exploring a new Attribute Association Graph?
                    When you use Neo4J Bloom for a new AAG, you need to add configurations for the visualization. 
                    If you are an advanced user and you want to query AAGs in Neo4J Browser, you can add visualization 
                    styling to adapt the Neo4J Browser looks to that of your AAGs in Bloom. Click on the drop-down to 
                    access the configuration files and a tutorial how to load 
                    them into Neo4J. If you have not installed Neo4J yet, please refer to 
                    "streamlit app (left sidebar)"->"Neo4J Installation" and come back here afterwards.
                    """
                    st.markdown(msg)
                    with st.expander('AAG Neo4J Configuration'):
                        config_msg = """
                        #### Configuration installation
                        
                        Below, you can read about the configuration installation and access the corresponding files.
                        
                        """
                        st.markdown(config_msg)
                        text_col, button_col = st.columns(2)
                        text_col.markdown('##### Installation in Neo4J Bloom')
                        if 'bloom_config' not in st.session_state:
                            with open(BLOOM_PATH) as f:
                                st.session_state.bloom_config = f.read()
                        button_col.download_button(
                            'Get Neo4J Bloom config', data=st.session_state.bloom_config,
                            file_name='graphxplore_neo4j_bloom_config.json',
                            mime='application/json')

                        config_msg = """
                        Before installation make sure that:
                        - Neo4J Desktop is running and the DBMS containing the AAG is running as well
                        - You have the config file ready, if not click on the button "Get Neo4J Bloom config" above
                        
                        In Neo4J Desktop/Bloom:
                        1. Click on the dropdown next to the blue "Open" button on the top right of the window, and 
                           click on "Neo4J Bloom"
                        2. After Neo4J Bloom opens, click on the control icon in the upper left corner of the windows 
                           and then on the button with "... Untitled Perspective..."
                        3. Select the database containing your AAG from the drop-down
                        4. Click on "Import" and select the GraphXplore config file
                        5. Click on the white card "GraphXplore AAG Config", an empty scene will open where you can 
                           explore your AAG!
                        """
                        st.markdown(config_msg)
                        st.image(get_how_to_image_path('bloom_aag_config'))
                        text_col, button_col = st.columns(2)
                        text_col.markdown('##### Installation in Neo4J Browser')
                        button_col.download_button(
                            'Get Neo4J Browser style', data=st.session_state.desktop_style,
                            file_name='graphxplore_neo4j_browser_style.grass',
                            mime='text/plain')
                        config_msg = """                        
                        Follow these steps to adjust the Neo4J Browser styling:
                        - Have Neo4J Desktop (or a Docker container) accessible and the DBMS containing the AAG running
                        - Click on the button "Get Neo4J Browser style" above and retrieve the styling file
                        - Open Neo4J Browser by clicking on the blue "Open" button on Neo4J Desktop, or access the 
                          Docker container Neo4J Browser
                        - Type "\:style" in the Neo4J Browser query command line
                        - Drag and drop the styling file, you are ready to go!
                        """
                        st.markdown(config_msg)
                        st.image(get_how_to_image_path('browser_aag_style'))

                    msg = """
                    ### Attribute Association Graph Navigation in Neo4J Bloom
                    
                    If you used Neo4J Bloom before, you will most likely be familiar with most of the functionalities 
                    described here. Notice that Neo4J Bloom was developed independently of GraphXplore and we only 
                    configured it to our needs. You don't need coding or scripting skills to operate Neo4J Bloom, your 
                    only interactions are via mouse-clicking and search bar prompts. For a quick start introduction by 
                    Neo4J developers themselves check out 
                    [https://neo4j.com/docs/bloom-user-guide/current/bloom-quick-start/](https://neo4j.com/docs/bloom-user-guide/current/bloom-quick-start/). 
                    If you are an advanced user and want to query the graph databases yourself, check out Neo4J Browser at 
                    [https://neo4j.com/docs/browser-manual/current/visual-tour/](https://neo4j.com/docs/browser-manual/current/visual-tour/). 
                    However, the rest of this guide will focus on Neo4J Bloom.
                    
                    #### Search Bar
                    
                    When you start your exploration, the main instrument will often be the search bar in the upper left 
                    corner. Here, you can display the whole graph or parts of it in three different ways:
                    - Type or click on "Show whole graph" to display the whole AAG. You can dismiss parts of the graph 
                      from the visualization later on
                    - Type or click on "Show subgraph of label " followed by a table or variable label assigned during 
                      metadata annotation. All available labels will be displayed for auto-completion. Press <Tab> to 
                      finish the statement. All attribute nodes with this label and their connecting edges will be 
                      added to the visualization
                    - Type or click on "Show subgraph with name containing " followed by a string. Press <Tab> to 
                      finish the statement. All attribute nodes with the string contained in their variable name 
                      together with their connecting edges will be added to the visualization
                    """
                    st.markdown(msg)

                    st.image(get_how_to_image_path('navigation_1'))

                    msg = """
                    #### Interacting with Nodes
                    
                    Nodes are depicted as colored circles with the variable name of the attribute displayed in bold and 
                    followed by the variable value. You can select nodes by clicking on them. If you want to select 
                    multiple nodes, you do so with pressing <Ctrl> while left-clicking. You can dismiss one or multiple 
                    nodes from the visualization by right-click->"Dismiss".  
                    You can inspect the data of a node by either double-clicking on it, 
                    or right-clicking and then choosing "Inspect". A window opens displaying all node labels and 
                    parameters. The labels are given in the upper part and the parameters in the lower part. If you 
                    want to read more about the parameter and label meanings, check out the tab "Properties" in 
                    GraphXplore.
                    """
                    st.markdown(msg)

                    st.image(get_how_to_image_path('navigation_2'))

                    msg = """
                    When right-clicking on one or multiple nodes, you can add edges and/or neighboring nodes:
                    - Add inter-connecting edges by clicking on "Reveal relationships"
                        - Only possible when you selected multiple nodes that share at least one edge
                    - Add neighboring nodes with
                        - "Expand" to add edges based on their type
                        - "Scene actions"->"Likely other attributes based on nodes" to add top 5 edges with highest 
                          summed conditional prevalence
                    """
                    st.markdown(msg)

                    st.image(get_how_to_image_path('navigation_3'))

                    msg = """
                    #### Interacting with Edges
                    
                    Edges are depicted as arrows with their type displayed directly above them. Same as nodes, you can 
                    select them via left-click or select multiple edges with <Ctrl>+left-click. You can dismiss one or 
                    multiple edges from the visualization by right-click->"Dismiss".  
                    You can inspect the data of the edge by double-clicking or right-click->"Inspect", a new window 
                    opens. The edge type is displayed on top of the window. In the middle, the edge parameters are 
                    shown. Explanation of edge type and parameters can be accessed at the tab "Properties" in 
                    GraphXplore. In the lower part of the window, the source and target node data are displayed and can 
                    be expanded.
                    """
                    st.markdown(msg)

                    st.image(get_how_to_image_path('navigation_4'))



            with aag_tabular_tab:
                NODE_PARAMS = {
                    'Count': ('count', True),
                    'Missing Ratio': ('missing', True),
                    'Prevalence': ('prevalence', True),
                    'Prevalence Difference': ('prevalence_difference', False),
                    'Prevalence Ratio': ('prevalence_ratio', False)
                }

                EDGE_PARAMS = {
                    'Co-Occurrence': ('co_occurrence', True),
                    'Conditional Prevalence': ('conditional_prevalence', True),
                    'Conditional Increase': ('conditional_increase', True),
                    'Conditional Increase Ratio': ('increase_ratio', True)
                }
                aag_table_db = VariableHandle(AAG_TABLE_DB_KEY).get_attr()
                aag_table = VariableHandle(AAG_TABLE_RESULT_KEY).get_attr()
                aag_table_groups = VariableHandle(AGG_TABLE_GROUPS_KEY).get_attr()

                if st.checkbox('Show tabular view tooltip'):
                    tabular_help_msg = """
                    Here, you can retrieve the :red[data of an attribute association graph in table form] and store the 
                    results as a CSV file. While this table-based data view removes the advantages of a visually driven 
                    data exploration, it becomes possible to :red[rank the graph data] based on some metric. 
                    Additionally, this table form enables the data transfer to other tools and/or publications. You can 
                    choose which metric to use for ranking, limit the number of results and select which node or edge 
                    parameters to display. For more a detailed explanation of the metrics used in an attribute 
                    association graph, please check out "Data Exploration"->"Intro to Attribute Association Graphs"
                    """
                    st.markdown(tabular_help_msg)

                get_database_select_widget(aag_tabular_tab, AAG_TABLE_DB_KEY,
                                           'Select Neo4J database for attribute association graph tabular view', False,
                                           GraphType.AttributeAssociation)
                object_col, param_col = st.columns(2)
                object_type_select = object_col.radio(
                    'Choose objects to retrieve from the database', ['Nodes', 'Edges'])
                param_options = NODE_PARAMS.keys() if object_type_select == 'Nodes' else EDGE_PARAMS.keys()
                parameter_select = param_col.selectbox('Choose metric for ranking', param_options)
                order_col, min_max_col = st.columns(2)
                order_select = order_col.radio('Choose ranking order', ['High values first', 'Low values first'])
                if parameter_select not in ['Prevalence Difference', 'Prevalence Quotient']:
                    min_max_select = min_max_col.radio(
                        'Choose min or max group metric for ranking', ['Max', 'Min'],
                        help='For this parameter the node contains a metric for each group separately. Choose which '
                             'value to use for the ranking')

                nof_results = st.slider('Choose number of results', 1, 200, 20)

                node_param_options = ['Reference Range'] + list(NODE_PARAMS.keys())

                if object_type_select == 'Nodes':
                    node_params_select = st.multiselect('Select which node parameters should be displayed',
                                                        node_param_options, default=node_param_options,
                                                        help='Name and value of nodes will always show')
                    query = 'match(x) return x.name as name, x.value as value, x.groups as groups'
                    if 'Reference Range' in node_params_select:
                        query += ', x.refRange as refRange'
                    for param in node_params_select:
                        if param in NODE_PARAMS:
                            query += ', x.' + NODE_PARAMS[param][0] + ' as ' + param.lower().replace(' ', '_').replace('-', '_')
                else:
                    query = 'match()-[x]->() with x '

                neo4j_param,use_agg = (NODE_PARAMS if object_type_select == 'Nodes' else EDGE_PARAMS)[parameter_select]

                if use_agg:
                    query += ', apoc.coll.' + min_max_select.lower() + '(x.' + neo4j_param + ') as agg'

                query += (' order by ' + ('agg' if use_agg else 'x.' + neo4j_param)
                          + (' desc' if order_select == 'High values first' else '') + ' LIMIT ' + str(nof_results))

                if object_type_select == 'Edges':
                    edge_param_col, node_param_col = st.columns(2)
                    edge_param_select = edge_param_col.multiselect('Select which edge parameters should be displayed',
                                                                   EDGE_PARAMS.keys(), default=EDGE_PARAMS.keys())
                    edge_node_params_select = node_param_col.multiselect('Select which node parameters should be displayed',
                                                                    node_param_options, default=['Prevalence', 'Reference Range'],
                                                                    help='Name and value of nodes will always show')
                    query += ' match (a)-[x]->(b) return x.groups as groups'
                    for cypher_var, prefix in [('a', 'condition'), ('b', 'outcome')]:
                        query += ', ' + cypher_var + '.name as ' + prefix + '_name, ' + cypher_var + '.value as ' + prefix + '_value'
                        if 'Reference Range' in edge_node_params_select:
                            query += ', ' + cypher_var + '.refRange as ' + prefix + '_refRange'
                        for param in edge_node_params_select:
                            if param in NODE_PARAMS:
                                query += ', ' + cypher_var + '.' + NODE_PARAMS[param][0] + ' as ' + prefix + '_' + param.lower().replace(' ', '_').replace('-', '_')
                    for param in edge_param_select:
                        query += ', x.' + EDGE_PARAMS[param][0] + ' as ' + param.lower().replace(' ', '_').replace('-', '_')

                st.button('Query database', type='primary', disabled=aag_table_db is None,
                          on_click=query_aag_for_table, args=[aag_tabular_tab, query],
                          help='You have to select a database containing an attribute association graph before querying it')

                if aag_table is not None:
                    if aag_table_groups is not None:
                        group_cols = st.columns(len(aag_table_groups))
                        for idx in range(len(aag_table_groups)):
                            group_cols[idx].markdown(aag_table_groups[idx])
                    st.dataframe(aag_table)
                    csv_data = convert_df(aag_table)
                    st.download_button('Store results as CSV', data=csv_data,
                                       file_name=aag_table_db + '_aag_data.csv', mime='text/csv')
                else:
                    st.info('No results retrieved yet')

            with dashboard_tab:
                get_dashboard_select_widget(dashboard_tab)

        with group_tab:
            if st.checkbox('Show group definition tooltip'):
                """
                Here, you can define groups of primary keys, e.g. a subgroup of patient having a condition or undergone 
                a certain procedure. Each group has a name, the primary key's origin table, and is specified by a 
                conditional logical expression. You might already know these logical expression from the data 
                transformation workflows in GraphXplore. This logical expression is used to later filter primary keys 
                by their associated attributes to either incorporate them in the group, or exclude them. You can use 
                your defined groups for the generation of attribute association graphs and to fine-tune your dashboards
                """
            defined_groups = VariableHandle(DEFINED_GROUP_KEY, init={}).get_attr()
            group_load_tab, group_edit_tab, group_store_tab = st.tabs(
                ['Load groups from JSON', 'View/edit groups', 'Store groups'])

            with group_load_tab:
                if st.checkbox('Show tooltip', key='group_load_tooltip'):
                    """
                    Here, you load predefined groups from a JSON file. All groups must be based on the same underlying 
                    metadata which you have to assign first. Upon uploading, the metadata and group definitions are 
                    matched. If a group name used in the JSON file already exists in the previously defined groups, it 
                    will be overwritten.
                    """
                group_load_meta = VariableHandle(GROUP_LOAD_META).get_attr()
                if group_load_meta is None:
                    st.info('You need to assign metadata to load predefined groups')
                    if main_meta is None:
                        st.info('You need to load/extract/create metadata at "Metadata" in the sidebar. Afterwards, '
                                'you can assign it here')
                else:
                    st.info('Currently assigned metadata has ' + str(len(group_load_meta.get_table_names()))
                            + ' table(s) and ' + str(group_load_meta.get_total_nof_variables()) + ' variables')
                st.button('Assign selected metadata', key='assign_meta_grou_load', disabled=main_meta is None,
                          on_click=lambda : VariableHandle(GROUP_LOAD_META).set_attr(main_meta))
                if group_load_meta is not None:
                    file_enc_load = st.selectbox(label='File encoding',
                                                 options=['auto', 'utf-8-sig', 'utf-8', 'ascii', 'ISO-8859-1'],
                                                 help='Select file encoding of JSON or detect automatically (default)')
                    loaded_group_file = st.file_uploader('Load predefined groups stored as JSON', type='json')
                    st.button('Load groups', type='primary', on_click=load_groups,
                              args=[group_load_tab, loaded_group_file, file_enc_load])

            with group_store_tab:
                if len(defined_groups) == 0:
                    st.info('No groups defined yet, that you can store')
                else:
                    if st.checkbox('Show group storage tooltip'):
                        """
                        Here, you can store your defined groups in a JSON to reload them at a later time. You can store 
                        multiple group definitions in the same file. However, all group definitions of one file must be 
                        based on the same underlying metadata. If you have group definitions based on different 
                        metadata objects, please store them in different files
                        """
                    group_names_to_store = st.multiselect(
                        'Choose which groups you want to store in one file', defined_groups.keys())
                    data_to_store = []
                    meta_dict_to_check = None
                    valid_selection = True
                    for group_name_to_store in group_names_to_store:
                        selector = defined_groups[group_name_to_store]
                        selector_meta = selector.meta.to_dict()
                        if meta_dict_to_check is not None and meta_dict_to_check != selector_meta:
                            first_group_name = data_to_store[0]['group_name']
                            st.error('Groups "' + first_group_name + '" and "' + group_name_to_store
                                     + '" cannot be stored together since they are based on different metadata')
                            valid_selection = False
                            break
                        elif meta_dict_to_check is None:
                            meta_dict_to_check = selector_meta
                        data_to_store.append({
                            'group_name' : group_name_to_store,
                            'group_table' : selector.group_table,
                            'condition' : str(selector.group_filter)
                        })
                    if valid_selection and len(data_to_store) > 0:
                        file_enc_group = st.selectbox(label='File encoding',
                                                      options=['utf-8', 'utf-8-sig', 'ascii', 'ISO-8859-1'],
                                                      help='Select file encoding of JSON')
                        json_data = json.dumps(
                            {'defined_groups' : data_to_store}, indent=6, ensure_ascii=False).encode(file_enc_group)
                        st.download_button('Store groups', data=json_data, file_name='defined_groups.json',
                                           mime='application/json')
            with group_edit_tab:
                st.subheader('Defined groups')
                if len(defined_groups) == 0:
                    st.info('No groups defined yet')
                else:
                    first = True
                    for group_name, group_selector in defined_groups.items():
                        if not first:
                            st.divider()
                        else:
                            first = False
                        st.markdown('**Group name**: ' + group_name)
                        st.markdown('**Group table**: ' + group_selector.group_table)
                        st.markdown('**Group condition**: ' + str(group_selector.group_filter))
                        st.button('Remove group "' + group_name + '"', on_click=defined_groups.pop,
                                  args=[group_name])


                with st.expander('Define new group'):
                    group_meta = VariableHandle(GROUP_META_KEY).get_attr()
                    group_lattice = VariableHandle(GROUP_LATTICE_KEY).get_attr()
                    if group_meta is None:
                        st.info('You need to assign metadata to define a new group')
                        if main_meta is None:
                            st.info('You need to load/extract/create metadata at "Metadata" in the sidebar. Afterwards, '
                                    'you can assign it here')
                    else:
                        st.info('Currently assigned metadata has ' + str(len(group_meta.get_table_names()))
                                + ' table(s) and ' + str(group_meta.get_total_nof_variables()) + ' variables')
                    def assign_group_meta():
                        VariableHandle(GROUP_META_KEY).set_attr(copy.deepcopy(main_meta))
                        VariableHandle(GROUP_LATTICE_KEY).set_attr(MetaLattice.from_meta_data(main_meta))
                    st.button('Assign selected metadata', disabled=main_meta is None,
                              on_click=assign_group_meta)
                    if group_meta is not None:
                        new_group_name_input = st.text_input('Insert group name')
                        group_table_input = st.selectbox(
                            'Choose table for group members', options=group_meta.get_table_names())
                        radio_col, help_col = st.columns(2)
                        selection = radio_col.radio('Should the group contain all primary keys?', ['Yes', 'No'])
                        cont = st.container()
                        if selection == 'Yes':
                            help_msg = f"""
                            All primary keys of table "{group_table_input}" will be part of the group. The condition 
                            will be a tautology always evaluating to true
                            """
                            condition = '(TRUE)'
                        else:
                            help_msg = f"""
                            Define a logical expression filtering the primary keys of table "{group_table_input}" to 
                            incorporate only a subset into the group
                            """
                            upward = set(group_lattice.get_relatives(group_table_input))
                            downward = set(group_lattice.get_relatives(group_table_input, False))
                            tables_for_single = [group_table_input] + [table for table in group_meta.get_table_names()
                                                                       if table in upward]
                            tables_for_agg = [table for table in group_meta.get_table_names() if table in downward]
                            condition_history_key = 'group_condition_history'
                            condition_def_widget = ConditionDefinition(
                                condition_history_key, group_meta, tables_for_single, tables_for_agg, for_mapping=False,
                                key='group_condition_def')
                            condition = st.session_state[condition_history_key][-1][0]
                            cont.markdown('**Current group condition**: ' + condition)
                            condition_def_widget.render(cont)

                        help_col.markdown(help_msg)
                        finished_definition = new_group_name_input != '' and '<placeholder>' not in condition
                        cont.button('Create new group', type='primary', disabled=not finished_definition,
                                    on_click=create_group, help='You need to insert a group name and complete the group '
                                                                'condition definition',
                                    args=[cont, group_meta, group_table_input, new_group_name_input, condition])

