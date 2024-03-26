import streamlit as st
from .utils import VariableHandle
from .common_state_keys import CURR_TASK
from .sub_tasks import WorkflowGoal, UploadData, ChooseMetaSource, TransformationMetaProcess, AssignConnection

class Workflow:
    def __init__(self):
        self.subtask_handle = VariableHandle(CURR_TASK)

    def _render_workflow_start(self):
        exp_msg = 'Want to start a new workflow?' if self.subtask_handle.get_attr() else 'Want to get help with your workflow?'
        with st.sidebar.expander(exp_msg):
            radio_col, help_col = st.columns(2)
            options = [entry.value for entry in [
                WorkflowGoal.ExtractMeta, WorkflowGoal.CleanData, WorkflowGoal.TransformData, WorkflowGoal.ExploreData,
                WorkflowGoal.OnTheFly]]
            workflow_opt = radio_col.radio('Select a workflow goal', options)
            if workflow_opt == WorkflowGoal.ExtractMeta.value:
                help_msg = """
                GraphXplore will generate metadata of your dataset by extracting variables, data types, 
                distributions, artifacts and primary/foreign key relations. You can review and adjust the extracted 
                information, add variable tags or descriptions, and annotate special or missing values. Afterwards, you can 
                store the resulting metadata for sharing with others, reproducibility, or usage in future GraphXplore workflows"""
                task = UploadData(WorkflowGoal.ExtractMeta)
            elif workflow_opt == WorkflowGoal.CleanData.value:
                help_msg = """
                GraphXplore will check for artifacts in your dataset or load pre-existing artifact 
                information. After you confirmed or adjusted the detected artifacts, an updated version of your dataset 
                will be generated"""
                task = ChooseMetaSource(WorkflowGoal.CleanData)
            elif workflow_opt == WorkflowGoal.TransformData.value:
                help_msg = """
                Use GraphXplore zu transform your dataset. You can split, combine and create new variables, or 
                aggregate data such as time series. The transformation will be documented in a mapping JSON consisting 
                of rules comprised of human-readable logical expressions for reuse or sharing with others. The mapping 
                definition is solely based on metadata and can be defined without access to the actual data"""
                task = TransformationMetaProcess()
            elif workflow_opt == WorkflowGoal.ExploreData.value:
                help_msg = """
                Use GraphXplore to visually analyze and explore your data. The dataset will be stored in a 
                graph database for efficient retrieval. Before exploring, you will have the option to define sub-groups 
                within your dataset such as disease and control cohorts. For exploration, you can view the data as 
                traditional plots, or use a graph-based visualization with *attribute association graphs*. 
                GraphXplore identifies patterns of interest in your data and these graphs highlight associations of 
                variables with groups, prevalence of attributes, and conditional dependencies with colors, shape sizes 
                and visually clustering"""
                task = AssignConnection()
            elif workflow_opt == WorkflowGoal.OnTheFly:
                help_msg = """
                You decide where you want to go with your workflow as GraphXplore guides you through the tasks. First, 
                you will load or extract metadata for your dataset. Depending on the results, you might want to clean 
                or transform your data, or jump straight into the exploration. You can mix and match the different 
                functionalities of GraphXplore at any time
                """
                task = ChooseMetaSource(WorkflowGoal.OnTheFly)
            else:
                raise NotImplementedError('Workflow help not implemented')
            help_col.markdown(help_msg)
            if self.subtask_handle.get_attr():
                validated = st.checkbox('Existing workflow will be overwritten')
                button_help = 'You have to check the upper box first'
            else:
                validated = True
                button_help = None
            st.button('Start workflow', type='primary', on_click=lambda : self.subtask_handle.set_attr(task),
                              disabled=not validated, help=button_help)

    def render(self):
        st.sidebar.subheader('Workflow Helper')

        curr_task = self.subtask_handle.get_attr()
        if curr_task and curr_task.done:
            st.sidebar.markdown('Workflow done! :tada:')
        counter = 0
        while counter < 4 and curr_task:
            task_widget = st.sidebar.expander(curr_task.header + (' :heavy_check_mark:' if curr_task.done else ''),
                                              expanded= not curr_task.done)
            curr_task.render(task_widget)
            counter += 1
            curr_task = curr_task.parent
        if counter > 1:
            def redo_last():
                curr_last_task = self.subtask_handle.get_attr()
                if curr_last_task.done:
                    curr_last_task.done = False
                    curr_last_task.done_triggered = False
                else:
                    new_last_task = curr_last_task.parent
                    new_last_task.done = False
                    new_last_task.done_triggered = False
                    self.subtask_handle.set_attr(new_last_task)
            st.sidebar.button('Redo last task', type='primary', on_click=redo_last)
        if counter > 0:
            st.sidebar.divider()
        self._render_workflow_start()