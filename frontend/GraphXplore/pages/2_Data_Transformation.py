import collections
import json
import streamlit as st
import copy
try:
    import pyodide
    DESKTOP_APP = True
except (ModuleNotFoundError, ImportError):
    DESKTOP_APP = False
import chardet
import pandas as pd
import pathlib
BASE_DIR = str(pathlib.Path(__file__).parents[1])
FRONTEND_DIR = str(pathlib.Path(__file__).parents[0])
import sys
sys.path.append(BASE_DIR)
sys.path.append(FRONTEND_DIR)
from src.io_widgets import CSVUploader, CSVDownloader
from src.logical_operator_widgets import ConditionDefinition, ConditionEdit
from src.utils import VariableHandle, ListHandle, ICON_PATH, FunctionWrapper
from src.common_state_keys import (MAIN_META_KEY, SOURCE_META_KEY, TARGET_META_KEY, MAIN_MAPPING_KEY,
                                   CLEAN_DATASET_META_KEY, CLEAN_DATASET_SOURCE_DATA_KEY, CLEAN_DATASET_RESULT_DATA_KEY,
                                   CLEAN_DATASET_DEL_ARTIFACTS_KEY, ADD_PK_SOURCE_DATA_KEY, ADD_PK_RESULT_DATA_KEY,
                                   TRANS_SOURCE_DATA_KEY, TRANS_RESULT_DATA_KEY, PIVOT_SOURCE_DATA_KEY, PIVOT_RESULT_DATA_KEY)
from src.workflow_widgets import Workflow
from graphxplore.MetaDataHandling import *
from graphxplore.DataMapping import *
from graphxplore.DataMapping.Conditionals import *
from graphxplore.DataMapping.Conclusions import *

CSV_LINE_THRESHOLD = 100000

def get_conclusion_widget(parent_obj, history_handle, source_tables_for_single, source_tables_for_agg):
    meta = VariableHandle(SOURCE_META_KEY).get_attr()
    if len(source_tables_for_agg) > 0:
        conclusion_options = ['Fixed return', 'Copy variable', 'Aggregate source data']
    else:
        conclusion_options = ['Fixed return', 'Copy variable']
    conclude_type_select = parent_obj.selectbox('Choose type of conclusion', conclusion_options)
    if conclude_type_select == 'Fixed return':
        data_type_select = parent_obj.selectbox('Choose data type', DataType.__members__)
        data_type = DataType._member_map_[data_type_select]
        if data_type == DataType.String:
            return_val = parent_obj.text_input('Insert return string')
        else:
            return_val = parent_obj.number_input('Insert return number', value=(0 if data_type == DataType.Integer else 0.0))
        conclude_str = 'RETURN ' + str(return_val) + ' OF TYPE ' + data_type
    elif conclude_type_select == 'Copy variable':
        table_col, var_col, data_type_col = parent_obj.columns(3)
        table_conc = table_col.selectbox('Choose source table for variable to copy', source_tables_for_single)
        var_conc = var_col.selectbox('Choose source variable to copy its value',
                                     meta.get_variable_names(table_conc))
        var_conc_data_type = meta.get_variable(table_conc, var_conc).data_type
        data_type_options = [var_conc_data_type.value] + [entry for entry in
                                                          DataType.__members__ if
                                                          entry != var_conc_data_type.value]
        data_type_conc = data_type_col.selectbox('Choose data type of values to copy', data_type_options,
                                                 help='Source variable values that do not match this data type '
                                                      'are not copied')
        conclude_str = ('COPY VARIABLE ' + var_conc + ' IN TABLE ' + table_conc + ' IF TYPE IS '
                        + DataType._member_map_[data_type_conc])
    else:
        agg_col, table_col, var_col, data_type_col = parent_obj.columns(4)
        agg_type_options = [entry for entry in AggregatorType.__members__ if entry != AggregatorType.List.name]
        agg_type_sel = agg_col.selectbox('Choose aggregation type of source data', agg_type_options,
                                         help='Count aggregated values, or concatenate aggregated values joined '
                                              'by semicolons. For aggregated numeric values the sum, min, max, '
                                              'mean, standard deviation, median or amplitude (max - min) can be '
                                              'calculated')
        agg_type = AggregatorType._member_map_[agg_type_sel]
        table_conc = table_col.selectbox('Choose source table for aggregation', source_tables_for_agg)
        var_conc = var_col.selectbox('Choose source variable for aggregation',
                                     meta.get_variable_names(table_conc))
        var_conc_data_type = meta.get_variable(table_conc, var_conc).data_type
        if agg_type in [AggregatorType.Min, AggregatorType.Max, AggregatorType.Mean, AggregatorType.Sum,
                        AggregatorType.Std, AggregatorType.Median, AggregatorType.Amplitude]:
            numeric_types = [DataType.Integer.value, DataType.Decimal.value]
            data_type_options = [var_conc_data_type.value] + [entry for entry in numeric_types if
                                                              entry != var_conc_data_type.value] if var_conc_data_type in numeric_types else numeric_types
        else:
            data_type_options = [var_conc_data_type.value] + [entry for entry in
                                                              DataType.__members__ if
                                                              entry != var_conc_data_type.name]
        data_type_conc = data_type_col.selectbox('Choose data type for aggregation', data_type_options,
                                                 help='Source variable values that do not match this data type '
                                                      'are not aggregated')
        conclude_str = 'AGGREGATE ' + agg_type + ' VARIABLE ' + var_conc + ' OF TYPE ' + data_type_conc + ' IN TABLE ' + table_conc

    parent_obj.button('Assign conclusion', on_click=history_handle.set_attr, args=[conclude_str])

    if '<placeholder>' not in history_handle.get_attr():
        parent_obj.success('Finished statement')

def build_mapping_case(parent_obj, condition_str, conclusion_str, var_mapping):
    try:
        conclusion = FixedReturnConclusion.from_string(conclusion_str)
        if conclusion is None:
            conclusion = CopyConclusion.from_string(conclusion_str)
        if conclusion is None:
            conclusion = AggregateConclusion.from_string(conclusion_str)
        if conclusion is None:
            raise AttributeError('Then-clause in new mapping case invalid: ' + conclusion_str)
        new_case = MappingCase(LogicOperatorParser.from_string(condition_str), conclusion)
        var_mapping.add_case(new_case)
    except AttributeError as new_case_error:
        parent_obj.error('ERROR: ' + str(new_case_error))

def update_order(error_container, var_mapping):
    adjusted_orders = [st.session_state['pos_case_' + str(idx)] for idx in range(len(var_mapping.cases))]
    visited = set()
    duplicates = [str(pos) for pos in adjusted_orders if pos in visited or visited.add(pos)]
    if len(duplicates) > 0:
        error_container.error('Position ' + ', '.join(duplicates) + ' selected multiple times')
    else:
        new_sorting = sorted([(adjusted_orders[idx], idx) for idx in range(len(adjusted_orders))])
        var_mapping.cases = [var_mapping.cases[idx] for pos, idx in new_sorting]

def get_mapping_widget(parent_obj, table_to_map, var_to_map):
    curr_mapping = VariableHandle(MAIN_MAPPING_KEY).get_attr()
    meta_to_map = VariableHandle(TARGET_META_KEY).get_attr()
    is_primary = meta_to_map.get_primary_key(table_to_map) == var_to_map
    is_inherited_fk = (var_to_map in meta_to_map.get_foreign_keys(table_to_map)
                       and curr_mapping.foreign_key_is_for_inheritance(table_to_map, var_to_map))
    if is_primary or is_inherited_fk:
        if is_primary:
            info_msg = f"""
            "{var_to_map}" is a primary key. Primary keys have no variable mapping. Their cell values after the 
            transformation are defined by the table mapping
            """
        else:
            foreign_table = meta_to_map.get_foreign_keys(table_to_map)[var_to_map]
            info_msg = f"""
            "{var_to_map}" is a foreign key with foreign table "{foreign_table}" which inherits the table mapping of 
            this table "{table_to_map}". Foreign keys which are used for inheritance have to variable mapping. Their 
            cell values after the transformation will be 0-indexed integers
            """
        parent_obj.info(info_msg)
    else:
        if parent_obj.checkbox('Show variable mapping tooltip'):
            parent_obj.markdown("""
            A :red[variable mapping] describes how the :red[value of a single target variable can be derived from a unit of 
            source data]. To read on how these units are generated from one or multiple source tables, please refer to the 
            tooltip in  "Target table mapping".\n  
            The variable mapping consist of one or multiple :red[mapping cases], which in turn consist of two logical 
            expressions: a :red[condition] (if-statement), and a :red[conclusion] (then-statement). The mapping cases are 
            processed in the presented order. If a case condition is met for the given unit of source data, its conclusion 
            is triggered and the target variable's value is generated. Subsequent cases are not checked. If no case's 
            condition is met, the empty string (a missing value) is assigned the the target variable for the given unit. 
            For information on how to define new cases, please click on "Show mapping case tooltip" below  
            """)
            st.divider()
        if st.checkbox('Show mapping case tooltip', key='mapping_case_tooltip'):
            """
            A mapping case consist of a condition which evaluates to true or false for each unit of source data. If 
            the condition evaluates to true, the conclusion is triggered.\n  
            The :red[condition] consists of :red[atomic] logical expressions which can be combined by nested 
            :red[negations], :red[disjunctions] (or) and :red[conjunctions] (and). The atomic logical expressions 
            can either be :red[tautologies] (always evaluate to true), or :red[check values of one source variable]. 
            For :red[singular variables] you can use :red[single value] atomic conditions, and for :red[aggregate 
            variables], you must use :red[aggregation] conditions. For the definition of singular and aggregate 
            variables, please refer to the tooltip in "Target table mapping".\n  
            The :red[conclusion] specifies the target variable's value, if the condition is met. It can either be a 
            :red[fixed return value], [copy] a singular source variable's value, or :red[aggregate] an aggregate 
            source variable's values. Depending on the variables data type, this can be a count, string 
            concatenation, or metric value aggregation such as median, mean, minimum etc
            """
            st.divider()
        var_mapping = curr_mapping.get_variable_mapping(table_to_map, var_to_map)
        if len(var_mapping.cases) == 0:
            parent_obj.markdown('**No mapping cases defined yet**')
        else:
            parent_obj.markdown('**Mapping cases**')
            if is_primary:
                parent_obj.info('Mapping cases of the primary key are not editable here. Refer to the "Target table mapping"')
            if is_inherited_fk:
                parent_obj.info('Mapping cases of foreign keys marking source dataset inheritance are not editable here. '
                                'Refer to the "Target table mapping"')
            positions = list(range(1, len(var_mapping.cases)+1))
            for idx in range(len(var_mapping.cases)):
                case = var_mapping.cases[idx]
                position = idx + 1
                parent_obj.markdown('**Case ' + str(position) + '**')
                disp_pos = [position] + [pos for pos in positions if pos != position]
                parent_obj.markdown('**If**: ' + str(case.conditional))
                parent_obj.markdown('**Then**: ' + str(case.conclusion))
                parent_obj.selectbox('Select position', disp_pos, key='pos_case_' + str(idx))
                parent_obj.button('Remove case', key='del_case_' + str(idx),
                                  on_click=var_mapping.remove_case, args=[idx])
                parent_obj.divider()

            parent_obj.button('Update order', disabled=len(var_mapping.cases) < 2, on_click=update_order,
                              args=[parent_obj, var_mapping])

        with parent_obj.expander('New mapping case') as new_case_expander:
            source_tables_for_single, source_tables_for_agg = curr_mapping.get_source_tables_for_var_mappings(
                table_to_map)
            condition_history_key = 'condition_history'
            condition_def_widget = ConditionDefinition(
                condition_history_key, st.session_state[SOURCE_META_KEY], source_tables_for_single, source_tables_for_agg)
            conclusion_history_key = 'conclusion_history'
            conclusion_history_handler = VariableHandle(conclusion_history_key, init=':red[<placeholder>]')
            new_case_state_viewer_cont = st.container()

            edit_mode_select = st.radio('Choose which statement to edit', ['If', 'Then'])

            block_edit_container = st.container()
            if edit_mode_select == 'If':
                condition_def_widget.render(block_edit_container)
            else:
                get_conclusion_widget(block_edit_container, conclusion_history_handler,
                                      source_tables_for_single, source_tables_for_agg)

            curr_condition = st.session_state[condition_history_key][-1][0]

            new_case_unfilled = ('<placeholder>' in curr_condition or '<placeholder>'
                                 in conclusion_history_handler.get_attr())

            st.button('Add new case', type='primary', disabled=new_case_unfilled, on_click=build_mapping_case,
                      args=[new_case_expander, curr_condition, conclusion_history_handler.get_attr(),
                            var_mapping])

            new_case_state_viewer_cont.markdown('**If**: ' + curr_condition)
            new_case_state_viewer_cont.markdown('**Then**: ' + conclusion_history_handler.get_attr())

def get_table_mapping_widget(parent_obj, curr_table) -> bool:
    with parent_obj.expander('Target table mapping'):
        if st.checkbox('Show table mapping tooltip'):
            """
            Each target table *x* must have some relationship to one or multiple source tables. 
            Using this relationship, single units of source data are formed. Variable mappings are applied to these 
            units to form a single output row of *x*. :red[Variables of the related source tables and their foreign 
            tables] (and their foreign tables, and so on...) will have a single value (might be a missing value) in 
            this unit of source data. These variables are called :red[singular variables]. :red[Variables of inverted 
            foreign tables] (*a* is an inverted foreign table of *b*, if *b* is a foreign table of *a*), might have 
            multiple values in a unit of source data (e.g. timeseries, or multiple blood measurements for a single 
            patient). They are called :red[aggregate variables]. For a table mapping you have the following options:
            * *x* has a :red[one-to-one] relationship with a single source table *y*. Primary key values are copied 
            from *y* to *x*. A unit of source data is formed by a single row of *y* and rows from
            foreign tables and/or inverted foreign tables of *y*. (Most common option)
            * *x* has a one-to-many relationship with multiple source tables. The data of the source tables (and 
            foreign tables or inverted foreign tables) will be combined to form a single unit of source data.
            This can be done in two ways:
                * The data of the source tables can be :red[merged]. Here, data rows from different source tables are 
                combined to a single unit, if the row's primary key values are identical. If a primary key value 
                of a source table has no analog in another source table, its row is taken independently.
                * The data of the source tables can be :red[concatenated]. Here, the source tables are processed 
                independently one after the other to form units of source data together with their foreign tables or 
                inverted foreign tables. The primary key values of *x* will be 0-indexed integers.
            * If *x* is a foreign table of another target table *x'*, the relationship to source tables can be 
            :red[inherited] from *x'*. If *x'* itself inherits the relationship of another target table *x''*, this 
            inheritance is propagated to *x*. The primary key values of *x* will be 0-indexed integers and all its rows 
            will be de-duplicated. The primary key values of *x* will be used as foreign key values in *x'*.
            
            Optionally, you can define a condition to filter out units of source data that should not be considered in 
            the mapping. Of the condition evaluates to false for a unit of source data, it is fully removed from the 
            transformation process. You can view the condition at the "If" below "Current table mapping". By default, 
            it is always true and all source data is considered
            """
            st.divider()
        curr_mapping = VariableHandle(MAIN_MAPPING_KEY).get_attr()
        table_mapping = curr_mapping.get_table_mapping(curr_table)
        if table_mapping.type is None:
            mapping_str = ':red[<UNASSIGNED>]'
        elif table_mapping.type == TableMappingType.Inherited:
            mapping_str = 'INHERIT MAPPING FROM TARGET TABLE "' + table_mapping.to_inherit + '"'
        elif table_mapping.type == TableMappingType.OneToOne:
            mapping_str = 'ONE-TO-ONE RELATION WITH SOURCE TABLE "' + table_mapping.source_tables[0] + '"'
        else:
            mapping_str = ('ONE-TO-MANY RELATION BY '
                           + ('CONCATENATING' if table_mapping.type == TableMappingType.Concatenate else 'MERGING')
                           + ' SOURCE TABLES "' + '", "'.join(table_mapping.source_tables) + '"')
        st.markdown('**Current table mapping**')
        st.markdown(mapping_str)
        st.markdown('**Condition** : ' + str(table_mapping.condition),
                    help='If this condition is not met for a unit of source data, no target data will be generated for '
                         'this unit. Defaults to be always true')
        st.divider()
        parents = []
        for parent in curr_mapping.target_lattice.parents[curr_table]:
            parent_mapping = curr_mapping.get_table_mapping(parent)
            if parent_mapping.type is not None:
                parents.append(parent)
        if len(parents) > 0:
            table_mapping_options = TableMappingType.__members__
        else:
            table_mapping_options = [entry for entry in TableMappingType.__members__
                                     if entry != TableMappingType.Inherited.name]
        if table_mapping.type is not None:
            table_mapping_options = [table_mapping.type.name] + [entry for entry in table_mapping_options
                                                                 if entry != table_mapping.type]
        if table_mapping.type == TableMappingType.Inherited:
            parents = [table_mapping.to_inherit] + [entry for entry in parents if entry != table_mapping.to_inherit]
        one_to_many_table_preselect = None
        if table_mapping.type in [TableMappingType.Merge, TableMappingType.Concatenate]:
            one_to_many_table_preselect = table_mapping.source_tables
        one_to_one_table_options = curr_mapping.source.get_table_names()
        if table_mapping.type == TableMappingType.OneToOne:
            one_to_one_table_options = table_mapping.source_tables + [entry for entry in one_to_one_table_options
                                                                      if entry not in table_mapping.source_tables]

        table_mapping_select_str = st.selectbox('Choose type of table mapping', table_mapping_options)
        table_mapping_select = TableMappingType._member_map_[table_mapping_select_str]
        if table_mapping_select == TableMappingType.OneToOne:
            one_to_one_table = st.selectbox('Choose source table for one-to-one relation', one_to_one_table_options)
            new_table_mapping = TableMapping(TableMappingType.OneToOne, [one_to_one_table])
        elif table_mapping_select == TableMappingType.Merge or table_mapping_select == TableMappingType.Concatenate:
            one_to_many_tables = st.multiselect('Choose source tables for one-to-many relation',
                                                curr_mapping.source.get_table_names(),
                                                default=one_to_many_table_preselect)
            if len(one_to_many_tables) < 2:
                st.error('At least two source tables must be selected for one-to-many relation')
            new_table_mapping = TableMapping(table_mapping_select, one_to_many_tables)
        else:
            table_to_inherit = st.selectbox('Choose target table to inherit relation to source dataset from', parents)
            new_table_mapping = TableMapping(TableMappingType.Inherited, to_inherit=table_to_inherit)

        mapping_unfinished = ((table_mapping_select == TableMappingType.Merge
                               or table_mapping_select == TableMappingType.Concatenate)
                              and len(one_to_many_tables) < 2)

        st.button('Assign target table mapping', type='primary', disabled=mapping_unfinished,
                  help='Before assignment, at least two source tables selected if relationship is one-to-many',
                  on_click=lambda : curr_mapping.assign_table_mapping(curr_table, new_table_mapping))

        if table_mapping.type is not None and table_mapping.type != TableMappingType.Inherited:
            table_condition_history_key = 'table_condition_history'
            source_tables_for_single, source_tables_for_agg = curr_mapping.get_source_tables_for_var_mappings(curr_table)
            init = [(':red[<placeholder>]', ConditionEdit.NewBlock),
                    ('(:red[<placeholder>])', ConditionEdit.StartAtomic),
                    ('(TRUE)', ConditionEdit.NewBlock)]
            table_condition_def_widget = ConditionDefinition(
                table_condition_history_key, curr_mapping.source, source_tables_for_single,
                source_tables_for_agg, history_init=init)
            st.divider()
            curr_new_condition_state = st.session_state[table_condition_history_key][-1][0]
            st.markdown('**New condition**: ' + curr_new_condition_state)

            table_condition_def_widget.render(st)

            st.button('Assign mapping condition', type='primary', disabled='<placeholder>' in curr_new_condition_state,
                      on_click= lambda : setattr(table_mapping, 'condition', LogicOperatorParser.from_string(curr_new_condition_state)))
    return table_mapping.type is not None

def clean_dataset(parent_obj, meta_for_copy, clean_source_data, clean_result_data):
    try:
        DataMappingUtils.copy_dataset(meta_for_copy, clean_source_data, clean_result_data, delete_artifacts=True)
        parent_obj.success('Dataset cleaned')
    except AttributeError as err:
        parent_obj.error('ERROR: ' + str(err))

def load_mapping(parent_obj, mapping_file, file_enc_mapping):
    if mapping_file is not None:
        try:
            if file_enc_mapping == 'auto':
                enc = chardet.detect(mapping_file.getvalue())['encoding']
                # ascii (without special characters) is subset of utf-8
                if enc == 'ascii':
                    enc = 'utf-8'
            else:
                enc = file_enc_mapping
            json_str = mapping_file.getvalue().decode(enc)
            data_mapping = DataMapping.from_dict(
                json.loads(json_str), VariableHandle(SOURCE_META_KEY).get_attr(),
                VariableHandle(TARGET_META_KEY).get_attr())
            VariableHandle(MAIN_MAPPING_KEY).set_attr(data_mapping)
            parent_obj.success('Loaded mapping successfully')
        except AttributeError as e:
            parent_obj.error('ERROR: ' + str(e))
    else:
        parent_obj.error('ERROR: You have to either select a file')

def get_overview_widget(parent_obj, curr_mapping: DataMapping):
    with parent_obj.expander('**Overview**'):
        if st.checkbox('Show tooltip', key='mapping_overview_tooltip'):
            """
            You can view all variable mappings in their current status in table form. One row of the table represents 
            one mapping case (with number) of one target variable. Rows with empty case, condition and conclusion cells 
            indicate, that no mapping cases exist for this variable yet. Otherwise, the mapping cases are shown in 
            ascending order.\n  
            You can double-click on a cell to display its full value. Additionally, you can display only variables, that 
            have at least one mapping case by clicking on the checkbox "Show only mapped variables"
            """
        show_only_mapped = st.checkbox('Show only mapped variables')
        overview_data = []
        one_table = len(curr_mapping.target.get_table_names()) == 1
        for tab in curr_mapping.target.get_table_names():
            for overview_var in curr_mapping.target.get_variable_names(tab):
                if not curr_mapping.variable_should_get_mapped(tab, overview_var):
                    continue
                var_mapping = curr_mapping.get_variable_mapping(tab, overview_var)
                row_dict = {} if one_table else {'table': tab}
                row_dict.update({'variable' : overview_var, 'case' : '', 'condition' : '', 'conclusion' : ''})

                if len(var_mapping.cases) == 0:
                    if not show_only_mapped:
                        overview_data.append(row_dict)
                    continue

                for idx in range(len(var_mapping.cases)):
                    case = var_mapping.cases[idx]
                    new_row_dict = copy.deepcopy(row_dict)
                    new_row_dict['case'] = str(idx+1)
                    new_row_dict['condition'] = str(case.conditional)
                    new_row_dict['conclusion'] = str(case.conclusion)
                    overview_data.append(new_row_dict)
        if len(overview_data) == 0:
            st.info('No variables for overview')
        else:
            df = pd.DataFrame(overview_data)
            st.dataframe(df, use_container_width=False, hide_index=True)


if __name__ == '__main__':
    st.set_page_config(page_title='Data Transformation', page_icon=ICON_PATH)
    st.title('Data Transformation')
    meta_handle = VariableHandle(MAIN_META_KEY)
    main_meta = meta_handle.get_attr()
    source_meta_handle = VariableHandle(SOURCE_META_KEY)
    source_meta = source_meta_handle.get_attr()
    target_meta_handle = VariableHandle(TARGET_META_KEY)
    target_meta = target_meta_handle.get_attr()
    mapping_handle = VariableHandle(MAIN_MAPPING_KEY)
    mapping = mapping_handle.get_attr()
    # if 'source_meta' not in st.session_state:
    #     st.session_state.source_meta = None
    # if 'target_meta' not in st.session_state:
    #     st.session_state.target_meta = None
    # if 'mapping' not in st.session_state:
    #     st.session_state.mapping = None

    workflow = Workflow()
    workflow.render()

    mapping_tab, transform_tab, utils_tab = st.tabs(['Data Mapping', 'Data Transformation', 'Utility'])

    with utils_tab:
        clean_tab, pk_tab, pivot_tab = st.tabs(['Clean dataset', 'Add primary key', 'Pivot table'])
        with clean_tab:
            if st.checkbox('Show tooltip', key='clean_tooltip'):
                """
                Here, you can clean your dataset from artifacts. Under the hood, a data transformation is performed 
                where all variable values get copied if they are no artifacts. :red[Only artifacts will be cleaned, 
                that are annotated in your metadata or do not match the variable data type]
                """
            clean_meta_handler = VariableHandle(CLEAN_DATASET_META_KEY)
            clean_meta = clean_meta_handler.get_attr()

            if clean_meta is None:
                st.info('Metadata of dataset to clean not yet assigned. You can use the tab "Meta Data" '
                        'to load or extract metadata and afterwards assign it here')
            else:
                st.success('Metadata of dataset to clean contains ' + str(len(clean_meta.get_table_names()))
                           + ' tables')
            st.button('Assign metadata', type='primary', disabled=main_meta is None,
                      help='disabled until metadata was selected' if main_meta is None else None,
                      on_click=clean_meta_handler.set_attr, args=[copy.deepcopy(main_meta)])
            if clean_meta is not None:

                result_data = VariableHandle(CLEAN_DATASET_RESULT_DATA_KEY, init={}).get_attr()

                clean_data_uploader = CSVUploader(CLEAN_DATASET_SOURCE_DATA_KEY,
                                                  'Choose CSV files for dataset cleaning',
                                                 required_tables=clean_meta.get_table_names(),
                                                 key='clean_upload')
                clean_data_uploader.render()
                source_data = VariableHandle(CLEAN_DATASET_SOURCE_DATA_KEY).get_attr()
                if len(source_data) == 0:
                    st.info('No CSV tables selected yet')
                else:
                    st.success('Selected table(s): "' + '", "'.join(source_data.keys()) + '"')

                    st.button('Clean dataset', type='primary',
                              on_click=clean_dataset,
                              args=[clean_tab, clean_meta, source_data, result_data])

                    if len(result_data) > 0:
                        clean_downloader = CSVDownloader(CLEAN_DATASET_RESULT_DATA_KEY, 'Store cleaned dataset',
                                                        'cleaned_dataset',
                                                        download_help='Will be a ZIP file if the dataset '
                                                                      'contains multiple tables or else a CSV file',
                                                        key='clean_download')
                        clean_downloader.render(clean_tab)

        with pk_tab:
            if st.checkbox('Show tooltip', key='add_pk_tooltip'):
                """
                Each table of your dataset is :red[required to have a primary key column] for GraphXplore's data transformation and 
                exploration functionalities. The primary key cell value of a data row can be thought of as its ID and 
                will be used to represent it during the mapping and exploration tasks. As the data row itself represent 
                data for some entity, its primary key in turn also represents this entity and can therefor be e.g. 
                a patient, event or specimen ID. A column can be a primary key, if all it's cell values are unique.
                If no such column exists in your dataset yet, :red[you can add a column with this functionality]. Its values 
                will be ascending integers starting from a given start index (defaults to 0).
                """
                st.divider()

            pk_add_data_uploader = CSVUploader(ADD_PK_SOURCE_DATA_KEY, 'Choose a CSV file for adding a primary key column',
                                               key='pk_add_upload', accept_multiple_files=False)
            pk_add_data_uploader.render()
            source_data = VariableHandle(ADD_PK_SOURCE_DATA_KEY).get_attr()
            if len(source_data) == 0:
                st.info('No CSV table selected yet')
            else:
                table_name = next(iter(source_data.keys()))
                st.success('Selected table: "' + table_name + '"')
                pk_name_col, idx_col, target_name_col = st.columns(3)
                pk_name = pk_name_col.text_input('Insert column name of primary key', table_name.lower() + '_pk')
                start_idx = idx_col.number_input('Choose start integer', 0,
                                                 help='Cell values for the primary key column will be ascending integers '
                                                      'starting from this value')
                target_pk_table = target_name_col.text_input('Insert name of result CSV table', table_name)
                result_data = VariableHandle(ADD_PK_RESULT_DATA_KEY, init={}).get_attr()

                def add_pk():
                    result_data.clear()
                    DataMappingUtils.add_primary_key(source_data, table_name,
                                                     result_data, target_pk_table, pk_name, start_idx)
                st.button('Generate new table', type='primary', on_click=add_pk)

                if len(result_data) > 0:
                    pk_add_data_downloader = CSVDownloader(ADD_PK_RESULT_DATA_KEY, 'Store generated table',
                                                           target_pk_table, key='pk_add_download')
                    pk_add_data_downloader.render()

        with pivot_tab:
            if st.checkbox('Show pivot tooltip'):
                pivot_msg = """
                Here, you can restructure your tables by :red[splitting up an *index column* into multiple new columns].
                Since can be useful to split up data of different types that is stored in one column, e.g. when moving 
                time series data from a narrow to a wide format.  
                :red[Each unique value of the index column] (or a subselection of your choice) :red[will form a new 
                column] in the result table. The cell values of these columns will be given by a *value column* of your 
                input table. Additionally, you may rename the newly created columns and/or exclude columns from the 
                input table for result generation. You can choose different index and value column and inspect the 
                result preview to get used with the concepts
                """
                st.markdown(pivot_msg)

            pivot_data_uploader = CSVUploader(
                PIVOT_SOURCE_DATA_KEY, 'Choose a CSV file for pivotization', key='pivot_upload',
                accept_multiple_files=False)
            pivot_data_uploader.render()
            source_data = VariableHandle(PIVOT_SOURCE_DATA_KEY).get_attr()
            if len(source_data) == 0:
                st.info('No CSV table selected yet')
            else:
                source_table = next(iter(source_data.values()))
                st.markdown('### Pivotization Parameters')
                source_variables = list(source_table[0].keys())
                index_col, value_col = st.columns(2)
                index_column = index_col.selectbox('Choose index column', options=source_variables,
                                                   help='Unique values of this column will form new columns in the '
                                                        'result table')
                value_column = value_col.selectbox(
                    'Choose value column', options=[column for column in source_variables if column != index_column],
                    help='Cell values of this row will fill the newly created columns'
                )
                all_index_vals_dict = collections.defaultdict(int)
                for row in source_table:
                    all_index_vals_dict[row[index_column]] += 1
                sorted_index_counts = sorted(all_index_vals_dict.items(),key=lambda x: x[1], reverse=True)
                index_vals, index_counts = zip(*sorted_index_counts)
                index_data = pd.DataFrame({
                    'index_value' : index_vals, 'count' : index_counts, 'use_value' : [True] * len(index_vals),
                    'target_column' : copy.deepcopy(index_vals)
                })
                index_data = st.data_editor(index_data, column_config={
                    'index_value' : st.column_config.Column('Value of "' + index_column + '"', disabled=True),
                    'count': st.column_config.Column('Number of occurrences', disabled=True,
                                                     help='Number of rows with this index value'),
                    'use_value' : st.column_config.CheckboxColumn(
                        'Use value for pivot', help='The checked values will create a new column in the result table',
                        default=True
                    ),
                    'target_column' : st.column_config.TextColumn('Column name in the result table', required=True)
                }, hide_index=True, disabled=['index_value', 'count'])
                columns_to_keep_options = [column for column in source_variables
                                           if column != index_column and column != value_column]
                columns_to_keep = st.multiselect(
                    'Which source table columns would you like to add to the result table?',
                    options=columns_to_keep_options, default=columns_to_keep_options)
                to_index = {}
                duplicate_target_cols = []
                source_target_cols = []
                used_some_index = False
                for index, row in index_data.iterrows():
                    if not row['use_value']:
                        continue
                    used_some_index = True
                    index_val = row['index_value']
                    target_column = row['target_column']
                    if target_column in to_index.values():
                        duplicate_target_cols.append(target_column)
                        continue
                    if target_column in columns_to_keep:
                        source_target_cols.append(target_column)
                        continue
                    to_index[index_val] = target_column
                if not used_some_index:
                    st.error('You must select at least one index value')
                elif len(duplicate_target_cols) > 0:
                    st.error('Target column name duplicate(s): "' + '", "'.join(duplicate_target_cols) + '"')
                elif len(source_target_cols) > 0:
                    st.error('Target column name(s) which are already source column name(s) "'
                             + '", "'.join(source_target_cols) + '"')
                else:
                    st.markdown('### Result Preview')
                    preview_data = []
                    counter = 0
                    for source_row in source_table:
                        target_row = {column : source_row[column] for column in columns_to_keep}
                        target_row.update({target_column : '' for target_column in to_index.values()})
                        set_column = source_row[index_column]
                        if set_column in to_index:
                            target_row[to_index[set_column]] = source_row[value_column]
                            preview_data.append(target_row)
                            counter += 1
                            if counter > 10:
                                break
                    preview_df = pd.DataFrame.from_records(preview_data)
                    st.dataframe(preview_df)

                    result_data = VariableHandle(PIVOT_RESULT_DATA_KEY, init={}).get_attr()

                    pivot_cont = st.container()

                    def pivot_data():
                        try:
                            result = DataMappingUtils.pivot_table(source_table, index_column, value_column, to_index,
                                                                  columns_to_keep)
                            VariableHandle(PIVOT_RESULT_DATA_KEY).set_attr({'pivoted_table' : result})
                            pivot_cont.success('Pivoted data')
                        except AttributeError as err:
                            pivot_cont.error('ERROR: ' + str(err))



                    pivot_cont.button('Pivot table', type='primary', on_click=pivot_data)

                    if len(result_data) > 0:
                        pk_add_data_downloader = CSVDownloader(PIVOT_RESULT_DATA_KEY, 'Store generated table',
                                                               'pivoted_table', key='pivot_download')
                        pk_add_data_downloader.render(pivot_cont)

    with mapping_tab:
        if st.checkbox('Show tooltip', key='mapping_tooltip'):
            """
            In GraphXplore, a :red[data mapping] describes how one dataset (here, called the :red[source dataset]) can be 
            :red[transformed into] another, potentially new dataset (here, called the :red[target dataset]). As a 
            prerequisite, :red[metadata for both datasets must exist]. Together, the mapping and the two metadata objects 
            fully describe a transformation workflow without containing the actual (potentially sensitive) data. 
            Therefore, they can be shared with others, or stored for reproducibility.\n  
            The data mapping is hierarchically ordered. On the top level, the :red[table mapping] describes the 
            :red[relationship of a table of the target dataset] to one or multiple tables of the source dataset. 
            Further information can be read later in the tooltip of "Target table mapping". On the lower level, 
            the :red[variable mapping] of a single variable of the target dataset :red[contains] one or multiple 
            :red[logical expressions], for :red[deriving the target variable's value] for a data unit (most often a 
            row of one table) of the source dataset. Further information can be read later in the tooltip 
            "Show variable mapping tooltip".
            """
        with st.expander('Metadata assignment'):
            if main_meta is None:
                st.info('Here, you can assign the source and target metadata. Before assignment, you must select '
                        'metadata in "Metadata" (left sidebar) by loading, extracting it from an existing dataset, or '
                        'creating it from scratch')
            else:
                source_msg_col, target_msg_col = st.columns(2)
                if source_meta is None:
                    source_meta_msg = """
                    Source metadata not yet assigned. You can navigate to "Metadata" in the sidebar to 
                    load/extract/create metadata and afterwards assign it here
                    """
                else:
                    source_meta_msg = ('Source metadata contains ' + str(len(source_meta.get_table_names()))
                                       + ' table(s) and ' + str(source_meta.get_total_nof_variables()) + ' variables')

                (source_msg_col.info if source_meta is None else source_msg_col.success)(source_meta_msg)

                if target_meta is None:
                    target_meta_msg = """
                    Target metadata not yet assigned. You can navigate to "Metadata" in the sidebar to 
                    load/extract/create metadata and afterwards assign it here
                    """
                else:
                    target_meta_msg = ('Target metadata contains ' + str(len(target_meta.get_table_names()))
                                       + ' table(s) and ' + str(target_meta.get_total_nof_variables()) + ' variables')

                (target_msg_col.info if target_meta is None else target_msg_col.success)(target_meta_msg)
                tables_without_pk = []
                for table in main_meta.get_table_names():
                    pk = main_meta.get_primary_key(table)
                    if pk == '':
                        tables_without_pk.append(table)
                if len(tables_without_pk) > 0:
                    st.error(
                        'In the selected metadata, the following table(s) have no primary key: "'
                        + '", "'.join(tables_without_pk)
                        + '". Each table of source and target needs a primary key for the data transformation')
                else:
                    st.info('Currently selected metadata has ' + str(len(main_meta.get_table_names()))
                            + ' table(s) and ' + str(main_meta.get_total_nof_variables())
                            + ' variables. Ready for assignment')
                    radio_col, help_col = st.columns(2)
                    assign_opt = radio_col.radio('Choose what to assign', ['Source', 'Target'])
                    handle_to_assign = source_meta_handle if assign_opt == 'Source' else target_meta_handle
                    agreed = True
                    if mapping is not None:
                        agreed = st.checkbox('This will reset the existing mapping')
                    def assign_meta():
                        (source_meta_handle if assign_opt == 'Source' else target_meta_handle).set_attr(
                            copy.deepcopy(main_meta))
                        mapping_handle.set_attr(None)
                    st.button(
                        'Assign', type='primary', on_click=assign_meta, disabled=not agreed,
                        help=None if agreed else 'You have to check that the existing mapping will be overwritten')

        st.subheader('Mapping')
        if source_meta is None or target_meta is None:
            st.info('You have to define metadata for the source and target dataset before you can define the mapping')
        else:
            select_tab, edit_tab, store_tab = st.tabs(['Select', 'View/Edit', 'Store'])
            with select_tab:
                load_tab, create_tab = st.tabs(['Load from JSON', 'Create new mapping'])
                with load_tab:
                    file_enc_load = st.selectbox(label='File encoding',
                                                 options=['auto', 'utf-8-sig', 'utf-8', 'ascii', 'ISO-8859-1'],
                                                 help='Select file encoding of JSON or detect automatically (default)')
                    loaded_mapping_file = st.file_uploader('Load mapping stored as JSON', type='json')
                    st.button('Load mapping', type='primary', on_click=load_mapping,
                              args=[load_tab, loaded_mapping_file, file_enc_load])
                with create_tab:
                    radio_col, help_col = st.columns(2)
                    create_opt = radio_col.radio('How do you want to create a new mapping?',
                                                 ['From Scratch', 'Initialize a copy mapping'])
                    invalid_table_vars = []
                    if create_opt == 'From Scratch':
                        help_msg = """
                        An empty mapping will be created. You will have to define all variable mappings manually
                        """
                    else:
                        help_msg = """
                        A mapping will be initialized, where all source variable values will get copied if their data 
                        type fits the data type of the target variable. Additionally, you can exclude artifacts values. 
                        Can only be used, if all target tables and variables also exist in the source metadata
                        """
                        for table in target_meta.get_table_names():
                            for var in target_meta.get_variable_names(table):
                                try:
                                    source_meta.get_variable(table, var)
                                except AttributeError as error:
                                    invalid_table_vars.append((table, var))
                    help_col.markdown(help_msg)
                    if len(invalid_table_vars) > 0:
                        st.error('Cannot initialize copy mapping, the following target variable(s) do not exist in the '
                                 'source metadata: "'
                                 + '", "'.join((var + '" in table "' + table for table, var in invalid_table_vars))
                                 + '"')

                    if create_opt == 'Initialize a copy mapping':
                        delete_artifacts = st.checkbox('Exclude artifacts from copying',
                                                       help='Artifacts are replaced by empty cells during the '
                                                            'transformation process')
                        create_func = lambda : mapping_handle.set_attr(DataMappingUtils.get_copy_mapping(
                            source_meta, target_meta, delete_artifacts))
                    else:
                        create_func = lambda : mapping_handle.set_attr(DataMapping(source_meta, target_meta))

                    button_cont = st.container()

                    button_cont.button('Create mapping', type='primary', disabled=len(invalid_table_vars) > 0,
                              on_click=FunctionWrapper.wrap_func, args=[button_cont, 'Mapping created', create_func])


            with edit_tab:
                if mapping is None:
                    st.info('You have to load or create a mapping before viewing or editing it')
                else:
                    unmapped_vars = 0
                    for table in target_meta.get_table_names():
                        for var in target_meta.get_variable_names(table):
                            if mapping.variable_should_get_mapped(table, var) and not mapping.variable_mapped(table, var):
                                unmapped_vars += 1
                    if unmapped_vars == 0:
                        st.success('Mapping is complete')
                    else:
                        st.info(str(unmapped_vars) + ' target variables are still unmapped')
                    get_overview_widget(edit_tab, mapping)
                    if st.checkbox('Show only target tables with unmapped variables'):
                        tables_to_show = [table for table in target_meta.get_table_names()
                                          if len([var for var in target_meta.get_variable_names(table)
                                                  if len(mapping.get_variable_mapping(table, var).cases) == 0]) > 0]
                    else:
                        tables_to_show = target_meta.get_table_names()
                    if len(tables_to_show) == 0:
                        st.info('No tables to show')
                    else:
                        table = st.selectbox('Select target table to view mapping', tables_to_show)
                        if len(target_meta.get_variable_names(table)) == 0:
                            st.info('Table "' + table + '" does not contain any variables')
                        elif not target_meta.has_primary_key(table):
                            st.info('Table "' + table
                                    + '" does not have a primary key yet. A primary key is mandatory for the '
                                      'mapping process for each table. You can assign one in "Meta Data" or add '
                                      'one in "Utility"->"Add primary key"')
                        else:
                            if not get_table_mapping_widget(st, table):
                                st.info('You have to define the table mapping before defining specific variable '
                                        'mappings')
                            else:
                                st.divider()
                                if st.checkbox('Show only unmapped target variables'):
                                    vars_to_show = [var for var in target_meta.get_variable_names(table)
                                                    if len(mapping.get_variable_mapping(table, var).cases) == 0]
                                else:
                                    vars_to_show = target_meta.get_variable_names(table)
                                if len(vars_to_show) == 0:
                                    st.info('No variables to show')
                                else:
                                    variable = st.selectbox('Select target variable to view mapping', vars_to_show)
                                    get_mapping_widget(edit_tab, table, variable)
                    st.divider()
                    agreed_to_reset = st.checkbox('All table and variable mappings will be removed')
                    st.button('Fully reset mapping', type='primary', disabled=not agreed_to_reset,
                              help='Remove all variable mappings and restart with an empty mapping',
                              on_click=lambda: VariableHandle(MAIN_MAPPING_KEY).set_attr(
                                  DataMapping(source_meta, target_meta)))

            with store_tab:
                if mapping is None:
                    st.info('Before storing, you have to define a mapping')
                else:
                    file_enc_download = st.selectbox(label='File encoding',
                                                     options=['utf-8', 'utf-8-sig', 'ascii', 'ISO-8859-1'],
                                                     help='Select file encoding of mapping JSON')
                    download_meta_file = st.download_button('Store data mapping',
                                                            data=json.dumps(mapping.to_dict(),
                                                                            indent=6,
                                                                            ensure_ascii=False).encode(
                                                                file_enc_download),
                                                            file_name='mapping.json', mime='application/json')

    with transform_tab:
        if st.checkbox('Show tooltip', key='transform_tooltip'):
            """
            Here, you can apply the data mapping you defined or loaded in "Data Mapping" to a matching source dataset 
            and generate the target dataset
            """
        if mapping is None or target_meta is None or not mapping.complete():
            st.info('You have to fully define the mapping before starting the data transformation process')
        else:

            data_mapping_uploader = CSVUploader(TRANS_SOURCE_DATA_KEY, 'Choose CSV files for data transformation',
                                                required_tables=source_meta.get_table_names())
            data_mapping_uploader.render()
            source_data = VariableHandle(TRANS_SOURCE_DATA_KEY).get_attr()
            if len(source_data) > 0:
                st.success('Selected table(s): "' + '", "'.join(source_data.keys()) + '"')
            else:
                st.info('No CSV tables selected yet')

            result_data = VariableHandle(TRANS_RESULT_DATA_KEY, init={}).get_attr()

            def transform_data_func():
                try:
                    data_trans = DataTransformation(mapping)
                    temp_result_data = {}
                    data_trans.transform_to_target(SourceDataType.CSV, source_data, temp_result_data)
                    VariableHandle(TRANS_RESULT_DATA_KEY).set_attr(temp_result_data)
                    transform_tab.success('Data transformation complete')

                except AttributeError as err:
                    transform_tab.error('ERROR: ' + str(err))

            st.button('Transform data', type='primary', disabled=len(source_data) == 0,
                      on_click=transform_data_func)
            if len(result_data) > 0:
                data_mapping_downloader = CSVDownloader(
                    TRANS_RESULT_DATA_KEY, 'Store transformed data', 'graphxplore_transformed_data',
                    key='data_mapping_download')
                data_mapping_downloader.render()
