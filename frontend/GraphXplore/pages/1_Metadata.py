import collections
import streamlit as st
import pandas as pd
import json
import chardet
import plotly.graph_objects as go
from dataclasses import asdict
try:
    import pyodide
    DESKTOP_APP = True
except (ModuleNotFoundError, ImportError):
    DESKTOP_APP = False
import pathlib
from typing import List, Optional, Dict, Any, Union, Tuple, Callable
BASE_DIR = str(pathlib.Path(__file__).parents[1])
FRONTEND_DIR = str(pathlib.Path(__file__).parents[0])
import sys
sys.path.append(BASE_DIR)
sys.path.append(FRONTEND_DIR)
from src.utils import FunctionWrapper, VariableHandle, ICON_PATH
from src.io_widgets import CSVUploader
from src.list_widgets import EditableList
from src.common_state_keys import MAIN_META_KEY, META_EXTRACT_DATA_KEY, CURR_TASK
from src.workflow_widgets import Workflow
from src.sub_tasks import WorkflowGoal, TriggerProcess
from graphxplore.MetaDataHandling import *
from graphxplore.Dashboard import *

CSV_LINE_THRESHOLD = 100000

def load_meta(parent_obj, loaded_meta_bytes, file_encoding: str):
    if loaded_meta_bytes is not None:
        try:
            if file_encoding == 'auto':
                enc = chardet.detect(loaded_meta_bytes.getvalue())['encoding']
                # ascii (without special characters) is subset of utf-8
                if enc == 'ascii' or enc == 'utf-8':
                    enc = 'utf-8-sig'
            else:
                enc = file_encoding
            json_str = loaded_meta_bytes.getvalue().decode(enc)
            VariableHandle(MAIN_META_KEY).set_attr(MetaData.from_dict(json.loads(json_str)))
            parent_obj.success('Loaded metadata')
        except AttributeError as e:
            parent_obj.error('ERROR: ' + str(e))
    else:
        parent_obj.error('ERROR: You have to select a file')

def extract_meta(parent_obj, data_dict : Dict[str, List[Dict[str, str]]], art_mode : ArtifactMode,
                 str_len_free_text : int, cat_threshold : int, bin_threshold : int, missing_vals_key: str):
    try:
        gen = MetaDataGenerator(data_dict, missing_vals=tuple(st.session_state[missing_vals_key]),
                                artifact_mode=art_mode,
                                nof_read_lines=CSV_LINE_THRESHOLD,
                                str_len_free_text=str_len_free_text, categorical_threshold=cat_threshold,
                                binning_threshold=bin_threshold)

        VariableHandle(MAIN_META_KEY).set_attr(gen.gather_meta_data())
        parent_obj.success('Finished metadata extraction')
        curr_task = VariableHandle(CURR_TASK).get_attr()
        if curr_task is not None and isinstance(curr_task,
                                                TriggerProcess) and curr_task.goal == WorkflowGoal.ExtractMeta:
            curr_task.done_triggered = True
    except AttributeError as err:
        parent_obj.error('ERROR: ' + str(err))

def store_meta(meta : MetaData, f_enc : Optional[str] = None):
    encoding = f_enc if f_enc is not None else 'utf-8'
    return json.dumps(meta.to_dict(), indent=6, ensure_ascii=False).encode(encoding)

@st.cache_data
def get_possible_foreign_keys(orig_table: str, table_vars : List[str], table_fks : List[str], all_pks : List[Tuple[str, str]]) -> Dict[str, List[str]]:
    result = collections.defaultdict(list)
    for var in table_vars:
        if var in table_fks:
            continue
        for other, other_pk in all_pks:
            if other == orig_table:
                continue
            if var == other_pk:
                result[var].append(other)
    return result

def show_distribution(parent_obj, distribution : Optional[Union[str, Dict[Any, float]]], dist_desc : Optional[str] = None,
                      none_desc : Optional[str] = None, none_help : Optional[str] = None,
                      tool_tip_label : Optional[str] = None, tool_tip_msg : Optional[str] = None):
    tooltip_cont = parent_obj.container()
    if distribution is None:
        if none_desc is not None:
            parent_obj.markdown(none_desc, help=none_help)
    else:
        if type(distribution) is dict:
            with parent_obj.expander(dist_desc):
                tooltip_cont = st.container()
                for dist_key, dist_val in distribution.items():
                    st.markdown(str(dist_key) + ' : ' + str(dist_val))
        else:
            st.markdown(dist_desc)
            st.markdown(distribution)
    if tool_tip_label and tool_tip_msg:
        if tooltip_cont.checkbox(tool_tip_label):
            tooltip_cont.markdown(tool_tip_msg)

def assign_thresholds(parent_obj, var_info: VariableInfo, current_lower: str, lower_input: str, current_upper: str,
                      upper_input: str):
    new_lower = var_info.binning.ref_low
    new_upper = var_info.binning.ref_high
    has_error = False
    if lower_input != current_lower:
        if lower_input == '':
            new_lower = None
        else:
            try:
                new_lower = float(lower_input)
            except ValueError:
                has_error = True
                parent_obj.error(lower_input + ' is not a number')

    if upper_input != current_upper:
        if upper_input == '':
            new_upper = None
        else:
            try:
                new_upper = float(upper_input)
            except ValueError:
                has_error = True
                parent_obj.error(upper_input + ' is not a number')

    if (new_lower is None) != (new_upper is None):
        parent_obj.error('Both reference parameters have to be set or none')
    elif new_lower is not None and new_lower > new_upper:
        parent_obj.error('Lower reference threshold is larger than upper one')
    elif not has_error:
        var_info.binning.ref_low = new_lower
        var_info.binning.ref_high = new_upper
        parent_obj.success('Thresholds assigned')

def get_artifact_mode_select_widget(parent_obj, key_stem):
    radio_col, help_col = parent_obj.columns(2)
    artifact_detection_select = radio_col.radio(
        'Choose level of artifact detection', ['Mismatch and outliers', 'Only mismatch', 'No detection'],
        key = key_stem + '_radio')
    if artifact_detection_select == 'Mismatch and outliers':
        help_msg = """
                    Cell values :red[not matching the most prominent data type] of the variable will be marked as artifacts. 
                    Additionally, :red[extreme outliers] are considered artifacts. For metric variables, these are cell 
                    values which have :red[no other value within 1.5 x interquartile range] (distance of first and third 
                    quartile). For categorical variables where the top 10 most frequent categories account for at 50% of 
                    the data, cell values which are not in the top 10 and :red[appear only once] are detected as artifacts
                    """
        artifact_mode = ArtifactMode.DataTypeMismatchAndOutliers
    elif artifact_detection_select == 'Only mismatch':
        help_msg = """
                    Cell values :red[not matching the most prominent data type] of the variable will be marked as artifacts.
                    """
        artifact_mode = ArtifactMode.OnlyDataTypeMismatch
    else:
        help_msg = """
                    No artifacts will be annotated
                    """
        artifact_mode = ArtifactMode.NoArtifacts
    help_col.markdown(help_msg)
    return artifact_mode

def show_variable_info(parent_obj, table_name, variable):
    parent_obj.subheader('Variable: ' + variable)
    meta_to_show = VariableHandle(MAIN_META_KEY).get_attr()
    var_info = meta_to_show.get_variable(table_name, variable)
    widget_key_stem = table_name + '_' + variable

    # variable and data type
    parent_obj.markdown('#### Types')
    var_type_col, data_type_col = parent_obj.columns(2)

    var_type_col.markdown('**Variable type**: ' + var_info.variable_type.value,
                          help='For changing primary or foreign keys, please go to "Table-wide information"'
                               ' or "Foreign keys"')
    if var_type_col.checkbox('Show variable type tooltip'):
        var_type_tool_tip = """
            In GraphXplore variables can either be primary keys, foreign keys, categorical, or metric variables. Primary 
            keys are explained in "Table-wide information", foreign keys in "Foreign keys" (only exists when you have 
            multiple tables in your dataset). :red[Metric variables must have an ordering] of their values and a concept of 
            :red[distance]. In addition, :red[metric variables must always have the data type integer or decimal]. 
            E.g. the weight and height of a human, or the travel time in minutes to a destination would be a metric 
            variable. In contrast, :red[categorical variables lack] this concept of :red[ordering or distance]. They can be 
            free text, boolean variables (either true or false), or represent any category such as blood groups, religion 
            or favorite dish
            """
        var_type_col.markdown(var_type_tool_tip)
    if var_info.variable_type not in [VariableType.PrimaryKey, VariableType.ForeignKey]:
        var_type_select_key = widget_key_stem + 'var_type_select'
        var_type_col.radio('Change variable type', [VariableType.Categorical.value, VariableType.Metric.value],
                           0 if var_info.variable_type == VariableType.Categorical else 1,
                           key=var_type_select_key,
                           on_change=lambda: setattr(var_info, 'variable_type',
                                                     VariableType._value2member_map_[
                                                         st.session_state[var_type_select_key]]))

    data_type_col.markdown('**Data type**: ' + var_info.data_type.value)
    if data_type_col.checkbox('Show data type tooltip'):
        data_type_tool_tip = """
            GraphXplore supports the three data types string, integer, and decimal. Integers and decimals are numbers, 
            where integers are positive and negative numbers without fractions or decimals. Therefore, integers are a 
            subset of decimals. A string is any sequence of written characters. If a variable contains any cell values, 
            that are not numbers and not artifacts, the variable should be of data type string. As all data is read from 
            CSV files (which are text files) by GraphXplore, all data read can be represented as string. 
            """
        data_type_col.markdown(data_type_tool_tip)
    data_type_options = [DataType.String.value, DataType.Integer.value, DataType.Decimal.value]
    data_type_select_key = widget_key_stem + 'data_type_select'

    data_type_col.radio('Change data type', data_type_options, data_type_options.index(var_info.data_type.value),
                        key=data_type_select_key, on_change=lambda:
        setattr(var_info, 'data_type', DataType._value2member_map_[st.session_state[data_type_select_key]]))

    if var_info.variable_type == VariableType.Metric and var_info.data_type == DataType.String:
        parent_obj.error('Metric variables cannot be strings')

    # value distribution and artifacts
    parent_obj.markdown('#### Value information')
    dist_col, artifact_col = parent_obj.columns(2)

    dist_col.markdown('##### Value distribution')

    var_dist_figs = VariableHandle('var_dist_figs', init=collections.defaultdict(dict)).get_attr()
    if dist_col.checkbox('Show value distribution tooltip'):
        dist_help_msg = """
        The value distribution is meant to give an overview about the values of a variable without disclosing potentially 
        privacy sensitive data. :red[It can only be extracted and not assigned manually]. :red[Metric variables] 
        will have an :red[whisker plot] containing information about median, first and third quartile, and potential 
        outliers. :red[Categorical variables] with the top 10 most frequent categories accounting for at least 50% of 
        variable data will have a :red[pie chart] as value distribution. All other variables (including primary and foreign 
        keys) will have no value distribution. For metric and categorical variables, you can recalculate the value 
        distribution (e.g. when you change the data type, variable type or adjusted the artifacts). This can only be done 
        by GraphXplore, if your underlying data set is currently loaded
        """
        dist_col.markdown(dist_help_msg)
    if var_info.value_distribution is None:
        dist_col.info('Value distribution was not extracted')
    else:
        value_dist_fig = MetadataDistributionPlotter.plot_value_distribution(var_info)
        dist_col.plotly_chart(value_dist_fig, use_container_width=True)
        missing_count_col, artifact_count_col = dist_col.columns(2)
        missing_count_col.metric('Missing value count', var_info.value_distribution.missing_count,
                                 help='Number of cells with a missing value')
        artifact_count_col.metric('Artifact count', var_info.value_distribution.artifact_count,
                                 help='Number of cells with an artifact value')

    artifact_col.markdown('##### Artifacts')
    if artifact_col.checkbox('Show artifact tooltip'):
        artifact_help_msg = """
        Artifacts are :red[erroneous cell values] which have to be handled when working with this variable. Artifacts 
        can be cell values not matching the data type of the variable, typos, measurement errors or extreme outliers.
        You can use GraphXplore to :red[clean your dataset] from these artifacts. When some values signify missing data 
        in one variable, but are non-missing in another, you can add them to the artifacts. During data exploration, 
        GraphXplore will exclude artifacts from the analysis
        """
        artifact_col.markdown(artifact_help_msg)

    if var_info.artifacts is None or len(var_info.artifacts) == 0:
        artifact_col.info('No artifacts annotated')
    else:
        with artifact_col.expander('Artifacts', expanded=False):
            art_exp_cols = st.columns(2)
            for idx in range(len(var_info.artifacts)):
                artifact = var_info.artifacts[idx]
                col_to_disp = art_exp_cols[idx % 2]
                col_to_disp.button(artifact, help='Click to remove', args=[artifact],
                                   on_click=lambda x : var_info.artifacts.remove(x))

    def add_artifact():
        new_artifact = st.session_state.artifact_add
        if var_info.artifacts is None:
            var_info.artifacts = [new_artifact]
        else:
            if new_artifact in var_info.artifacts:
                artifact_col.error('Artifact already annotated')
            else:
                var_info.artifacts.append(new_artifact)
    artifact_col.text_input('Add artifact', key='artifact_add', on_change=add_artifact)

    extract_data = VariableHandle(META_EXTRACT_DATA_KEY).get_attr()
    if (extract_data is not None
            and table_name in extract_data
            and len(extract_data[table_name]) > 0
            and variable in extract_data[table_name][0]):

        if parent_obj.toggle('Recalculate distribution and artifacts'):
            recalc_cont = parent_obj.container()

            recalc_radio_col, recalc_help_col = recalc_cont.columns(2)
            artifact_recalc_select = recalc_radio_col.radio(
                'Choose level of artifact adding', ['Add mismatch', 'Add mismatch and outliers', 'Add no artifacts'],
                key=widget_key_stem + '_radio_recalc')
            if artifact_recalc_select == 'Add mismatch and outliers':
                recalc_help_msg = """
                Add cell values :red[not matching the most prominent data type] of the variable to existing artifacts. 
                Additionally, :red[extreme outliers] are considered artifacts. For metric variables, these are cell 
                values which have :red[no other value within 1.5 x interquartile range] (distance of first and third 
                quartile). For categorical variables where the top 10 most frequent categories account for at 50% of 
                the data, cell values which are not in the top 10 and :red[appear only once] are detected as artifacts
                """
                recalc_artifact_mode = ArtifactMode.DataTypeMismatchAndOutliers
            elif artifact_recalc_select == 'Add mismatch':
                recalc_help_msg = """
                Add cell values :red[not matching the most prominent data type] of the variable to artifacts.
                """
                recalc_artifact_mode = ArtifactMode.OnlyDataTypeMismatch
            else:
                recalc_help_msg = """
                Only existing artifacts will remain and no new artifacts will be added during recalculation
                """
                recalc_artifact_mode = ArtifactMode.NoArtifacts
            recalc_help_col.markdown(recalc_help_msg)

            recalc_missing_vals_key = 'recalc_missing_vals'

            recalc_missing_vals = EditableList(recalc_missing_vals_key,
                                               ['', 'NaN', 'Na', 'NA', 'NAN', 'nan', 'na'],
                                               list_help='These values are considered as synonyms for unfilled data and '
                                                         'are excluded from the value distribution and artifact detection')
            recalc_missing_vals.render(recalc_cont.expander('Missing values for recalculation'))

            def recalc_dist_artifacts():
                var_data = collections.defaultdict(int)
                for row in extract_data[table_name]:
                    var_data[row[variable]] += 1
                var_info.detect_artifacts_and_value_distribution(
                    var_data, artifact_mode=recalc_artifact_mode,
                    missing_vals=st.session_state[recalc_missing_vals_key])
                recalc_cont.success('Finished recalculation')

            recalc_cont.button('Start recalculation', on_click=recalc_dist_artifacts, type='primary')
            parent_obj.divider()

    # description and labels
    parent_obj.markdown('#### Description and Labels')
    desc_col, label_col = parent_obj.columns(2)

    desc_col.markdown('##### Description')

    if desc_col.checkbox('Show description tooltip'):
        desc_help_msg = """
        The description of a variable is :red[fully optional]. It should :red[explain the meaning of the variable] to 
        you or other users of your metadata. It could e.g. contain the unit of measurement for a metric variable or 
        describe the categories of a categorical variable. When using this metadata to build attribute association 
        graphs, this description will be written into the nodes of the graph representing attributes of this variable
        """
        desc_col.markdown(desc_help_msg)

    if var_info.description is None:
        desc_col.info('Description not yet assigned')
        desc_str = ''
    else:
        if '\n' in var_info.description:
            multiline_str = var_info.description.replace('\n', '  \n')
            desc_col.markdown('**Description**:  \n' + multiline_str)
        else:
            desc_col.markdown('**Description**: ' + var_info.description)
        desc_str = var_info.description
    desc_key = widget_key_stem + 'desc_select'
    desc_col.text_area(
        'Write a variable description', value=desc_str, key=desc_key,
        on_change=lambda : setattr(var_info, 'description', st.session_state[desc_key].strip()
        if st.session_state[desc_key].strip() != '' else None))

    label_col.markdown('##### Labels')
    if label_col.checkbox('Show label tooltip'):
        label_help_msg = """
        Variable labels are broad categories such as "Measurement", "Condition", "Outcome". You can use labels to group 
        variables. GraphXplore will add them to nodes of all generated graphs und you can explore parts of your dataset 
        using these labels
        """
        label_col.markdown(label_help_msg)
    if len(var_info.labels) == 0:
        label_col.info('No labels assigned')
    else:
        label_disp_cols = label_col.columns(2)
        for idx in range(len(var_info.labels)):
            label = var_info.labels[idx]
            label_disp_cols[idx % 2].button(
                label, help='Click to remove', on_click=lambda x: var_info.labels.remove(x), args=[label])
    def add_label():
        try:
            var_info.add_label(st.session_state.add_label)
        except AttributeError as err:
            label_col.error(str(err))
    label_col.text_input('Add label', key='add_label', on_change=add_label)

    with parent_obj.expander('#### Advanced'):
        st.markdown('##### Binning')
        if st.checkbox('Show binning tooltip'):
            """
            This section is only relevant if you want to use GraphXplore for graph-based data exploration. During 
            base graph generation, GraphXplore will :red[assign all values of a metric variable to one of three bins] 
            "low" (below reference range), "normal" (within reference range), and "high" (above reference range). This way 
            semantics are added to the individual metric values. If a metric variable is assigned for binning, but no 
            reference range is specified here, GraphXplore will automatically detect a reference range containing the 
            middle 60% of the data using percentiles. Additionally you can specify values which should not get binned. 
            This could e.g. be -99 marking invalid measurements."""

        if var_info.binning is None:
            msg_col, but_col = st.columns(2)
            msg_col.markdown('**Binning information not assigned**')
            but_col.button('Create binning information',
                           on_click=lambda: setattr(var_info, 'binning', BinningInfo(should_bin=False)))
        else:
            bin_select_key = widget_key_stem + '_should_bin_select'

            radio_cont = st.container()

            def change_binning():
                if st.session_state[bin_select_key] == 'True' and var_info.data_type == DataType.String:
                    radio_cont.error('String variables cannot be binned, will stay unmarked')
                else:
                    var_info.binning.should_bin = st.session_state[bin_select_key] == 'True'

            radio_cont.radio('Bin Variable', ['True', 'False'], 0 if var_info.binning.should_bin else 1,
                           key=bin_select_key, on_change=change_binning)
            if var_info.binning.should_bin:
                lower_val = '' if var_info.binning.ref_low is None else str(var_info.binning.ref_low)
                lower_col, upper_col = st.columns(2)
                lower_input = lower_col.text_input(
                    'Insert lower reference threshold', value=lower_val,
                    help='Values below this threshold will be assigned to the "low" bin. If no values should be '
                         'considered "low" you can assign the threshold "-inf"')
                upper_val = '' if var_info.binning.ref_high is None else str(var_info.binning.ref_high)
                upper_input = upper_col.text_input(
                    'Insert upper reference threshold', value=upper_val,
                    help='Values above this threshold will be assigned to the "high" bin. If no values should be '
                         'considered "high" you can assign the threshold "inf"')
                button_cont = st.container()
                button_cont.button(
                    'Assign thresholds', on_click=assign_thresholds,
                    args=[button_cont, var_info, lower_val, lower_input, upper_val, upper_input])
                st.markdown('###### Values to exclude from binning')
                exclude_vals = var_info.binning.exclude_from_binning
                if exclude_vals is None or len(exclude_vals) == 0:
                    st.info('No values excluded from binning')
                else:
                    exclude_cols = st.columns(len(exclude_vals))
                    for idx in range(len(exclude_vals)):
                        exclude_val = exclude_vals[idx]
                        exclude_cols[idx].button(
                            str(exclude_val), help='Click to remove', key='exclude_' + str(exclude_val),
                            on_click=lambda x : exclude_vals.remove(x), args=[exclude_val])
                insert_cont = st.container()
                def add_exclude_val():
                    val_to_add = st.session_state.bin_exclude_insert
                    if val_to_add in exclude_vals:
                        insert_cont.error('Value already excluded')
                    else:
                        exclude_vals.append(val_to_add)

                insert_cont.number_input(
                    'Insert a number to exclude', key='bin_exclude_insert', value=-1.0)

                insert_cont.button('Add exclusion', on_click=add_exclude_val)

        st.markdown('##### Data Type Distribution')

        if st.checkbox('Show data type distribution tooltip'):
            """
            A data type distribution gives you the ratio of occurrence of all three data types in the variable's 
            values. In "clean" datasets, only one data type should be present for the variable. This distribution can 
            help you to detect artifacts in your dataset and decide on the data type of the variable
            """

        if var_info.data_type_distribution is None:
            st.info('Data type distribution was not extracted')
        else:
            data_type_fig = MetadataDistributionPlotter.plot_data_type_distribution(var_info)
            st.plotly_chart(data_type_fig, use_container_width=True)

        st.markdown('##### Default Value and Revision')
        default_col, reviewed_col = st.columns(2)
        default_col.markdown('###### Default value')

        if default_col.checkbox('Show default value tooltip'):
            default_val_msg = """
            The default value (if set) will be used for data exploration, but :red[is optional].
            :red[Rows with missing values] for this variable, :red[will be assigned the default value]
            """
            default_col.markdown(default_val_msg)

        default_key = widget_key_stem + 'default_val_input'
        default_val_msg = '**Default value not set**' if var_info.default_value is None else '**Default value**: ' + str(
            var_info.default_value)
        default_val_str = '' if var_info.default_value is None else str(var_info.default_value)
        default_col.markdown(default_val_msg)

        def adjust_default_value():
            default_val_input = st.session_state[default_key]
            if default_val_input == '':
                var_info.default_value = None
            else:
                casted_def_val = var_info.cast_value_to_data_type(default_val_input)
                if casted_def_val is None:
                    default_col.error('ERROR: Default value "' + default_val_input + '" is not of type '
                                      + var_info.data_type.value)
                else:
                    var_info.default_value = casted_def_val

        default_col.text_input('Insert or change default value', value=default_val_str, key=default_key,
                               on_change=adjust_default_value)

        reviewed_col.markdown('###### Revision')

        if reviewed_col.checkbox('Show revision tooltip'):
            review_msg = """
            You can use this status to remind you or communicate with others which :red[variables were manually 
            reviewed and approved]. You can :red[filter tables and variables by their status]. However, the variable 
            review status :red[is optional] and will not be used by GraphXplore
            """
            reviewed_col.markdown(review_msg)
        reviewed_str = 'Unassigned' if var_info.reviewed is None else 'Reviewed' if var_info.reviewed else 'Not reviewed'
        reviewed_col.markdown('**Variable status**: ' + reviewed_str)
        reviewed_options = ['Reviewed', 'Not reviewed', 'Unassigned']
        reviewed_key = widget_key_stem + 'reviewed_select'
        reviewed_col.radio('Change status', reviewed_options, reviewed_options.index(reviewed_str), key=reviewed_key,
                           on_change=lambda: setattr(var_info, 'reviewed',
                                                     None if st.session_state[reviewed_key] == 'Unassigned' else
                                                     True if st.session_state[reviewed_key] == 'Reviewed' else False))

        st.divider()

        del_var_button_col, del_var_toggle_col = st.columns(2)

        del_var_ok = del_var_toggle_col.toggle('Really permanently delete the variable?')

        del_var_button_col.button('Delete Variable', type='primary', on_click=FunctionWrapper.wrap_func,
                          args=[parent_obj, None, meta_to_show.remove_variable, table, variable],
                          disabled=not del_var_ok)

def init_show_filters(parent_obj, to_filter : str):
    if to_filter not in ['table', 'variable']:
        raise AttributeError('Filter only written for tables and variables')
    filter_key = to_filter + '_filters'
    func_key = to_filter + '_filter_funcs'
    if filter_key not in st.session_state:
        st.session_state[filter_key] = []
    if func_key not in st.session_state:
        st.session_state[func_key] = {}
    if len(st.session_state[filter_key]) == 0:
        parent_obj.markdown('No ' + to_filter + ' filters selected')
    else:
        def reset_filter():
            st.session_state[filter_key] = []
            st.session_state[func_key] = {}

        def remove_single_filter(filter_to_del):
            st.session_state[filter_key].remove(filter_to_del)
            del st.session_state[func_key][filter_to_del]

        parent_obj.button('Reset filter', type='primary', key=to_filter + '_filter_reset', on_click=reset_filter)
        for filter_name in st.session_state[filter_key]:
            parent_obj.button(filter_name, help='Click to remove', on_click=remove_single_filter,
                              args=[filter_name])

def add_filter(parent_obj, to_filter : str, filter_name: str, filter_func: Callable, include: bool):
    filter_key = to_filter + '_filters'
    func_key = to_filter + '_filter_funcs'
    if filter_name not in st.session_state[filter_key]:
        st.session_state[filter_key].append(filter_name)
        st.session_state[func_key][filter_name] = (filter_func, include)
    else:
        parent_obj.error('Filter already selected')


def get_table_filter_widget(parent_obj):
    if parent_obj.checkbox('Show tooltip', key='table_filter_checkbox'):
        tool_tip = """
        Configure which tables to view. Filtered tables will still be part of the final metadata. You can remove single 
        added filters by clicking on them, or fully reset all filters
        """
        parent_obj.markdown(tool_tip)
    init_show_filters(parent_obj, 'table')
    get_meta = VariableHandle(MAIN_META_KEY).get_attr
    builder_container = parent_obj.container()
    filter_select = builder_container.selectbox('Choose filter type', ['None', 'Name Substring', 'Has Variable Substring',
                                                                       'Has Primary Key', 'Has Foreign Keys',
                                                                       'Has Unreviewed Variables',
                                                                       'Has Variables with Artifacts'])
    incl_excl = builder_container.radio('Include or exclude table on match', ('Include', 'Exclude'), disabled=filter_select == 'None')
    if filter_select != 'None':
        incl_excl_str = ' ' if incl_excl == 'Include' else ' no ' if 'Has' in filter_select else ' not '
        if filter_select == 'Name Substring':
            sub_str = builder_container.text_input('Insert table substring')
            table_filter = 'Table name' + incl_excl_str + 'contains "' + sub_str + '"'
            filter_func = lambda x:  sub_str in x
        elif filter_select == 'Has Variable Substring':
            sub_str = builder_container.text_input('Insert variable substring')
            table_filter = 'Table has' + incl_excl_str + 'variable with substring "' + sub_str + '"'
            filter_func = lambda x: len([var for var in get_meta().get_variable_names(x) if sub_str in var]) > 0
        elif filter_select == 'Has Primary Key':
            table_filter = 'Table has' + incl_excl_str + 'primary key assigned'
            filter_func = lambda x: get_meta().has_primary_key(x)
        elif filter_select == 'Has Foreign Keys':
            table_filter = 'Table has' + incl_excl_str + 'foreign keys assigned'
            filter_func = lambda x: len(get_meta().get_foreign_keys(x)) > 0
        elif filter_select == 'Has Unreviewed Variables':
            table_filter = 'Table has' + incl_excl_str + 'unreviewed variables'
            filter_func = (lambda x: len([var for var in get_meta().get_variable_names(x)
                                          if get_meta().get_variable(x, var).reviewed is None
                                          or not get_meta().get_variable(x, var).reviewed]) > 0)
        else:
            table_filter = 'Table has' + incl_excl_str + 'variables with artifacts'
            filter_func = (lambda x: len([var for var in get_meta().get_variable_names(x)
                                          if get_meta().get_variable(x, var).artifacts is not None
                                          and len(get_meta().get_variable(x, var).artifacts) > 0]) > 0)
        builder_container.button('Add filter', on_click=add_filter, key='table_add_filter',
                                 args=[builder_container, 'table', table_filter, filter_func, incl_excl == 'Include'])

def filter_tables() -> List[str]:
    tables_to_filter = VariableHandle(MAIN_META_KEY).get_attr().get_table_names()
    if len(st.session_state.table_filters) == 0:
        return tables_to_filter
    result = []
    for table_to_filter in tables_to_filter:
        is_ok = True
        for filter_name, (filter_func, incl) in st.session_state.table_filter_funcs.items():
            if filter_func(table_to_filter) != incl:
                is_ok = False
                break
        if is_ok:
            result.append(table_to_filter)
    return result


def get_variable_filter_widget(parent_obj):
    init_show_filters(parent_obj, 'variable')
    get_meta = VariableHandle(MAIN_META_KEY).get_attr
    builder_container = parent_obj.container()
    filter_select = builder_container.selectbox('Choose filter type',
                                                ['None', 'Name Substring', 'Variable Type',
                                                 'Data Type', 'Has Description', 'Binned',
                                                 'Reviewed', 'Has Artifacts'])
    incl_excl = builder_container.radio('Include or exclude variable on match', ('Include', 'Exclude'),
                                        disabled=filter_select == 'None')
    if filter_select != 'None':
        incl_excl_str = ' ' if incl_excl == 'Include' else ' no ' if 'Has' in filter_select else ' not '
        if filter_select == 'Name Substring':
            sub_str = builder_container.text_input('Insert variable substring')
            var_filter = 'Variable name' + incl_excl_str + 'contains "' + sub_str + '"'
            filter_func = lambda tab, var: sub_str in var
        elif filter_select == 'Variable Type':
            var_type = builder_container.selectbox('Select variable type', VariableType.__members__)
            var_filter = 'Variable is' + incl_excl_str + ' of type ' + var_type
            filter_func = lambda tab, var: get_meta().get_variable(tab, var).variable_type.value == var_type
        elif filter_select == 'Data Type':
            data_type = builder_container.selectbox('Select variable type', DataType.__members__)
            var_filter = 'Variable is' + incl_excl_str + ' of data type ' + data_type
            filter_func = lambda tab, var: get_meta().get_variable(tab, var).data_type.value == data_type
        elif filter_select == 'Has Description':
            var_filter = 'Variable has' + incl_excl_str + 'description'
            filter_func = (lambda tab, var: get_meta().get_variable(tab, var).description is not None
                                     and get_meta().get_variable(tab, var).description != '')
        elif filter_select == 'Binned':
            var_filter = 'Variable' + incl_excl_str + 'marked for binning'
            filter_func = (lambda tab, var: get_meta().get_variable(tab, var).binning is not None
                                     and get_meta().get_variable(tab, var).binning.should_bin)
        elif filter_select == 'Reviewed':
            var_filter = 'Variable' + incl_excl_str + 'marked as reviewed'
            filter_func = (lambda tab, var: get_meta().get_variable(tab, var).reviewed is not None
                                     and get_meta().get_variable(tab, var).reviewed)
        else:
            var_filter = 'Table has' + incl_excl_str + ' artifacts'
            filter_func = (lambda tab, var: get_meta().get_variable(tab, var).artifacts is not None
                                     and len(get_meta().get_variable(tab, var).artifacts) > 0)

        builder_container.button('Add filter', on_click=add_filter,
                                 args=[builder_container, 'variable', var_filter, filter_func, incl_excl == 'Include'])

def filter_variables(table_name) -> List[str]:
    vars_to_filter = VariableHandle(MAIN_META_KEY).get_attr().get_variable_names(table_name)
    if len(st.session_state.variable_filters) == 0:
        return vars_to_filter
    result = []
    for var_to_filter in vars_to_filter:
        is_ok = True
        for filter_name, (filter_func, incl) in st.session_state.variable_filter_funcs.items():
            if filter_func(table_name, var_to_filter) != incl:
                is_ok = False
                break
        if is_ok:
            result.append(var_to_filter)
    return result

def get_meta_overview_widget(parent_obj):
    with parent_obj.expander('##### Variable Overview'):
        if st.checkbox('Show tooltip', key='overview_tooltip'):
            """
            View all variables of all tables with their variable type, data type, description, binning and review 
            information, value distribution, and artifacts
            """
        overview_data = []
        overview_meta = VariableHandle(MAIN_META_KEY).get_attr()
        one_table = len(overview_meta.get_table_names()) == 1
        for tab in overview_meta.get_table_names():
            for var in overview_meta.get_variable_names(tab):
                var_info = overview_meta.get_variable(tab, var)
                row_dict = {} if one_table else {'table' : tab}
                row_dict.update({
                    'variable': var,
                    'variable_type': var_info.variable_type.value,
                    'data_type': var_info.data_type.value,
                    'description': var_info.description,
                    'binned': False if not var_info.binning or not var_info.binning.should_bin else True,
                    'reviewed': False if not var_info.reviewed else True,
                    'distribution' : asdict(var_info.value_distribution) if var_info.value_distribution is not None else None,
                    'artifacts' : var_info.artifacts
                })
                overview_data.append(row_dict)
        if len(overview_data) == 0:
            st.info('Metadata contains to variables')
        else:
            df = pd.DataFrame(overview_data)
            st.dataframe(df, use_container_width=True)


if __name__ == '__main__':
    st.set_page_config(page_title='Metadata', page_icon=ICON_PATH)
    st.title('Metadata')
    meta_handle = VariableHandle(MAIN_META_KEY)
    meta = meta_handle.get_attr()
    workflow = Workflow()
    workflow.render()
    if meta is None:
        st.info('No metadata selected yet')
    else:
        st.info('Metadata has ' + str(len(meta.get_table_names())) + ' table(s), and '
                + str(meta.get_total_nof_variables()) + ' variables in total')
    select_tab, view_tab, store_tab = st.tabs(['Select', 'View/Edit', 'Store'])

    with select_tab:
        load_tab, extract_tab, create_tab = st.tabs(["Load from JSON", "Extract from Data", "Create from Scratch"])
        with load_tab:
            file_enc_load = st.selectbox(label='File encoding',
                                         options=['auto', 'utf-8-sig', 'utf-8', 'ascii', 'ISO-8859-1'],
                                         help='Select file encoding of JSON or detect automatically (default)')
            loaded_meta_file = st.file_uploader('Load metadata stored as JSON', type='json', key='meta_file_loader')
            st.button('Load metadata', type='primary', on_click=load_meta, args=[load_tab, loaded_meta_file, file_enc_load])

        with extract_tab:
            extract_tab.markdown('Extract metadata from one or multiple CSV files')


            extract_data_uploader = CSVUploader(META_EXTRACT_DATA_KEY, 'Choose CSV files for metadata extraction')
            extract_data_uploader.render()
            meta_extract_data = st.session_state[META_EXTRACT_DATA_KEY]
            if len(meta_extract_data) > 0:
                st.success('Selected table(s): "' + '", "'.join(meta_extract_data.keys()) + '"')
            else:
                st.info('No CSV tables selected yet')

            artifact_mode_extract = get_artifact_mode_select_widget(extract_tab, 'extract')

            meta_extract_missing_vals_key = 'meta_extract_missing_vals'

            missing_vals_list = EditableList(meta_extract_missing_vals_key, ['', 'NaN', 'Na', 'NA', 'NAN', 'nan', 'na'],
                                             list_help='These values are considered as synonyms for unfilled data and '
                                                       'are excluded from the metadata extraction')
            missing_vals_list.render(extract_tab.expander('Missing values'))

            with extract_tab.expander('Advanced parameters'):

                st.markdown('**Categorical threshold**')

                categorical_threshold = st.number_input(
                    'Variables with at most this number of distinct values are considered categorical variables.'
                    'Integer or decimal variables with more distinct values are considered metric variables. For '
                    'categorical variables with at most this number of distinct values, a distribution will be inferred.',
                    value=20, min_value=1)

                st.markdown('**Binning threshold**')

                binning_threshold = st.number_input(
                    'Metric variables with more distinct values are marked for binning',
                    value=20, min_value=1)

                st.markdown('**Free text threshold**')

                free_text_str_len = st.number_input('Strings with at least this length are considered free text',
                                                    value=300, min_value=1)

            extract_tab.button('Extract metadata', type='primary', disabled=len(meta_extract_data) == 0,
                               on_click=extract_meta, args=[extract_tab, meta_extract_data, artifact_mode_extract,
                                                            free_text_str_len, categorical_threshold, binning_threshold,
                                                            meta_extract_missing_vals_key])

        with create_tab:
            create_help = """
            Insert one or multiple table names. When this metadata gets coupled with a dataset, the CSV file names of 
            the dataset must match these tables names without ".csv" extension
            """
            table_list = EditableList('meta_create_tables', list_help=create_help)
            table_list.render(create_tab.expander('Table names'))
            meta_handle = VariableHandle('meta')
            cont = st.container()
            cont.button('Create metadata', type='primary', on_click=FunctionWrapper.wrap_func,
                        args=[cont, 'Created metadata', meta_handle.set_attr,
                              MetaData(st.session_state.meta_create_tables)])

    with view_tab:
        if meta is None:
            st.info('You have to select metadata for viewing and editing it')
        else:
            table_add_container = st.container()
            add_table_name = table_add_container.text_input('Insert table name',
                                                       help='Tables names are file names without ".csv" extension')
            table_add_container.button('Add table', on_click=FunctionWrapper.wrap_func,
                                       args=[table_add_container, None, meta.add_table, add_table_name],
                                       help='You should only use this functionality, when creating metadata for '
                                            'a new dataset such as the target of a data transformation')
            st.divider()
            if len(meta.get_table_names()) == 0:
                st.info('metadata does not contain any tables yet')
            else:
                get_meta_overview_widget(view_tab)
                if len(meta.get_table_names()) > 1:
                    table_filter_exp = st.expander('**Table filter**')
                    get_table_filter_widget(table_filter_exp)
                    filtered_tables = filter_tables()
                    if len(filtered_tables) == 0:
                        table_filter_exp.error('No tables remain after filtering, table list not updated')
                        tables_to_show = meta.get_table_names()
                    else:
                        if len(st.session_state.table_filters) != 0:
                            table_filter_exp.success(str(len(filtered_tables)) + ' tables remain after filtering')
                        tables_to_show = filtered_tables
                    table = st.selectbox('Select table to view', tables_to_show)
                    st.divider()
                else:
                    table = meta.get_table_names()[0]
                st.subheader('Table: ' + table)
                with st.expander('##### Table-wide information') as table_exp:
                    label_container = st.container()
                    label_container.markdown('##### Table Label')
                    label_container.markdown('**Label**: ' + meta.get_label(table))
                    label_input_key = 'table_label'
                    def adjust_label():
                        FunctionWrapper.wrap_func(label_container, None, meta.assign_label, table,
                                                  st.session_state[label_input_key])
                    label_container.text_input('Assign table label',
                                               value=meta.get_label(table),
                                               key=label_input_key,
                                               on_change=lambda:
                                               FunctionWrapper.wrap_func(label_container, None,
                                                                         meta.assign_label, table,
                                                                         st.session_state[label_input_key]),
                                               help='This label functions as an alias for your table. By default, it is '
                                                    'the file name of the CSV without the ".csv" extension. You can '
                                                    'reset it, if you would like a different or more intuitive '
                                                    'representation of this table')
                    var_add_container = st.container()
                    add_var_name = var_add_container.text_input(
                        'Insert variable name to add', key=table + '_add_var_name',
                        help='You should only use this functionality, when creating metadata for '
                             'a new dataset such as the target of a data transformation')
                    var_add_container.button('Add variable', key=table + '_add_var_button',
                                             on_click=FunctionWrapper.wrap_func,
                                             args=[var_add_container, None, meta.add_variable,
                                                   table, add_var_name],
                                             help='You should only use this functionality, when creating metadata for '
                                                  'a new dataset such as the target of a data transformation')
                    pk_container = st.container()
                    pk_container.markdown('##### Primary key')
                    pk = meta.get_primary_key(table)
                    if pk_container.checkbox('Show primary key tooltip', key='pk_tooltip'):
                        pk_tooltip = """
                        Primary keys are a fundamental concept in data representation. The primary key is a variable of 
                        a table which cell values can be thought of as the row ID. Each table of your dataset is 
                        :red[required to have a primary key column] for GraphXplore's data transformation and 
                        exploration functionalities and it will be used to represent it during the transformation and 
                        exploration tasks. As the data row itself represents data for some entity, its primary key in 
                        turn also represents this entity and can therefore be e.g. 
                        a patient, event or specimen ID. :red[A column can be a primary key, if all it's cell values are unique].
                        If no such column exists in your dataset yet, :red[you can add a column with this functionality] at
                        "Data Transformation" (sidebar on the left)-> "Utility" -> "Add primary key"
                        """
                        pk_container.markdown(pk_tooltip)
                        pk_container.divider()
                    if pk == '':
                        pk_container.info('Primary key not yet assigned')
                    else:
                        pk_container.markdown('**Primary key**: ' + pk)
                    if len(meta.get_variable_names(table)) > 0:
                        if pk == '':
                            sorted_vars = meta.get_variable_names(table)
                        else:
                            sorted_vars = [pk] + [var for var in meta.get_variable_names(table) if var != pk]
                        pk_selection = pk_container.selectbox('Select a variable with unique values as primary key',
                                                              sorted_vars, key=table + '_select_pk',
                                                              help='Changing the primary key will also change foreign key references in other tables')
                        pk_container.button('Change primary key', key=table + '_change_pk',
                                            on_click=FunctionWrapper.wrap_func,
                                            args=[pk_container, None, meta.change_primary_key, table,
                                                  pk_selection])

                    if len(meta.get_table_names()) > 1:
                        fk_cont = st.container()
                        fk_cont.markdown('##### Foreign keys')
                        if fk_cont.checkbox('Show foreign keys tooltip'):
                            """
                            :red[Foreign keys] are variables of this table that :red[are primary keys of another table] 
                            (called foreign table). As a result, each row of this table has a connection to a single row of the 
                            foreign table. E.g. this table could contain laboratory measurements, and the foreign table 
                            could contain patient information with a patient ID as primary key (foreign key in the 
                            laboratory measurements table). The foreign key would tell you for which patient the 
                            measurement was taken, and you could get further information on the patient in the foreign 
                            table.
                            """
                        fks = meta.get_foreign_keys(table)
                        if len(fks) == 0:
                            fk_cont.info('No foreign keys assigned')
                        else:
                            for fk, ft in fks.items():
                                fk_cont.button('"' + fk + '" of foreign table "' + ft + '"',
                                               help="Click to remove", on_click=FunctionWrapper.wrap_func,
                                               args=[fk_cont, None, meta.remove_foreign_key, table, fk])
                        poss_new_fks = get_possible_foreign_keys(table, meta.get_variable_names(table),
                                                                 list(fks.keys()),
                                                                 [(other, meta.get_primary_key(other))
                                                                  for other in meta.get_table_names()])
                        if len(poss_new_fks) == 0:
                            fk_cont.info('No other foreign keys assignable. Foreign keys must be primary keys in their '
                                         'origin table')
                        else:
                            fk_col, ft_col = fk_cont.columns(2)
                            fk_select = fk_col.selectbox('Select a foreign key', poss_new_fks.keys())
                            ft_select = ft_col.selectbox(
                                'Select a foreign table', poss_new_fks[fk_select],
                                help='Most often a variable name will only be used in one table as primary key')
                            fk_cont.button('Assign foreign key', on_click=FunctionWrapper.wrap_func,
                                           args=[fk_cont, None, meta.add_foreign_key, table, ft_select,
                                                 fk_select])

                    st.divider()
                    del_button_col, del_toggle_col = st.columns(2)
                    del_okay = del_toggle_col.toggle('Really fully delete table?')
                    del_button_col.button(
                        'Delete table', type='primary', key=table + '_del', on_click=FunctionWrapper.wrap_func,
                        args=[table_exp, None, meta.remove_table, table], disabled=not del_okay)

                st.divider()
                if len(meta.get_variable_names(table)) == 0:
                    st.markdown('Table "' + table + '" does not contain any variables yet')
                else:
                    variable_filter_exp = st.expander('##### Variable filter')
                    get_variable_filter_widget(variable_filter_exp)
                    filtered_vars = filter_variables(table)
                    if len(filtered_vars) == 0:
                        variable_filter_exp.error('No variables remain after filtering, variable list not updated')
                        vars_to_show = meta.get_variable_names(table)
                    else:
                        if len(st.session_state.variable_filters) != 0:
                            variable_filter_exp.success(str(len(filtered_vars)) + ' variables remain after filtering')
                        vars_to_show = filtered_vars
                    selected_var = st.selectbox('Select variable to view', vars_to_show)
                    st.divider()
                    show_variable_info(st, table, selected_var)

    with store_tab:
        if meta is None:
            st.info('You have to select metadata before storing it')
        else:
            file_enc_download = st.selectbox(label='File encoding',
                                             options=['utf-8', 'utf-8-sig', 'ascii', 'ISO-8859-1'],
                                             help='Select file encoding of JSON')
            download_meta_file = st.download_button('Store metadata',
                                                    data=store_meta(meta, file_enc_download),
                                                    file_name='meta.json', mime='application/json')





