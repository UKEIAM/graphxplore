import streamlit as st
from .common_state_keys import (CURR_TASK, MAIN_META_KEY, META_EXTRACT_DATA_KEY, ADD_PK_SOURCE_DATA_KEY,
                                ADD_PK_RESULT_DATA_KEY, CLEAN_DATASET_META_KEY, CLEAN_DATASET_SOURCE_DATA_KEY,
                                CLEAN_DATASET_RESULT_DATA_KEY, SOURCE_META_KEY, MAIN_MAPPING_KEY,
                                TARGET_META_KEY, TRANS_SOURCE_DATA_KEY, TRANS_RESULT_DATA_KEY, NEO4J_ADDRESS_KEY,
                                NEO4J_AUTH_KEY, TRANSLATION_META_KEY, TRANSLATION_SOURCE_DATA_KEY,
                                DASHBOARD_META_KEY, DASHBOARD_DB_KEY, DASHBOARD_BASIS_TABLE, DEFINED_GROUP_KEY,
                                GROUP_META_KEY, GROUP_LOAD_META, AAG_META_KEY, AAG_INPUT_DB_KEY, AAG_POS_GROUP,
                                AAG_CHOSEN_GROUPS, AAG_NEG_GROUP, AAG_TABLE_DB_KEY, AAG_TABLE_RESULT_KEY)
from typing import Optional
from enum import Enum

class WorkflowGoal(str, Enum):
    ExtractMeta = 'Extract Metadata'
    CleanData = 'Clean Dataset'
    TransformData = 'Transform Dataset'
    ExploreData = 'Explore Dataset'
    AddPrimaryKey = 'Add Primary Key to Dataset'
    OnTheFly = 'Let Me Decide on the Fly'
    CreateMeta = 'Create Metadata from Scratch'
    CreateBaseGraph = 'Convert your Dataset into a Graph Database'
    CreateAAG = 'Generate Attribute Association Graph'
    ExploreAAG = 'Explore Attribute Association Graph'
    ExploreDashboard = 'Explore Dashboard'
    DefineGroup = 'Define Groups'

class Subtask:
    def __init__(self, header: str, goal: WorkflowGoal, parent: Optional['Subtask']=None,
                 add_source_target_suffix: bool = True):
        self.goal = goal
        self.parent = parent
        self.done = False
        self.header = header
        if add_source_target_suffix and parent is not None:
            source_suffix = self.get_source_target_suffix(True)
            target_suffix = self.get_source_target_suffix(False)
            if source_suffix in parent.header:
                self.header += source_suffix
            elif target_suffix in parent.header:
                self.header += target_suffix
        self.uid = 0 if parent is None else parent.uid + 1
        self.widget_key_stem = 'task_' + str(self.uid)
        self.done_triggered = False

    def render_mark_done(self, parent_obj, child: Optional['Subtask'], button_label : Optional[str] = None):
        def mark_done():
            self.done = True
            if child:
                st.session_state[CURR_TASK] = child
        if not self.done:
            button_disp = 'Done' if button_label is None else button_label
            parent_obj.button(button_disp, key=self.widget_key_stem + '_' + button_disp.replace(' ', '_').lower(),
                              on_click=mark_done)

    def render(self, parent_obj):
        raise NotImplementedError('Never call the parent class')

    @staticmethod
    def get_source_target_suffix(use_source: bool) -> str:
        return ' for ' + (':red[Source]' if use_source else ':blue[Target]')


class FinishedMeta(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask']=None):
        super().__init__('Finish Metadata', goal, parent)

    def render(self, parent_obj):
        msg = """
        - You finished the metadata inspection :tada:
        - You can store the generated metadata at "Store"->"Store metadata". Optionally you can 
          adjust the file encoding
        - You can reload the stored metadata from JSON at any time at "Metadata" (in the sidebar)->"Select"->"Load 
          from JSON" """
        parent_obj.markdown(msg)
        if not self.done:
            options = ['Clean artifacts from dataset'] if st.session_state[MAIN_META_KEY].has_artifacts() else []
            if self.get_source_target_suffix(True) in self.header or self.get_source_target_suffix(False) in self.header:
                options_to_add = ['Use metadata as is']
            else:
                options_to_add = ['Finish workflow', 'Explore dataset', 'Transform dataset']
            options += options_to_add
            if len(options) > 1:
                dec_col, help_col = parent_obj.columns(2)
                decision = dec_col.radio('How do you want to proceed?', options, key=self.widget_key_stem + '_proceed')
                if decision == 'Clean artifacts from dataset':
                    help_msg = """
                    In the next step, you will create a new version of your dataset by removing the artifacts annotated in 
                    the metadata. Afterwards, you could transform or start exploring your data with GraphXplore, or use any 
                    other tool at your disposal
                    """
                    child = AssignMeta(WorkflowGoal.CleanData, self)
                elif decision == 'Finish workflow':
                    help_msg = """
                    You are done with the workflow and GraphXplore will stop guiding you for now. If you want to start a 
                    new workflow, you can do so at any time
                    """
                    child = None
                elif decision == 'Explore dataset':
                    if self.goal == WorkflowGoal.CreateBaseGraph:
                        help_msg = """
                        Use the metadata to convert your dataset into a graph database
                        """
                        child = AssignMeta(self.goal, self)
                    elif self.goal == WorkflowGoal.CreateAAG:
                        help_msg = """
                        Use the metadata to generate an attribute association graph
                        """
                        child = AssignMeta(self.goal, self)
                    elif self.goal == WorkflowGoal.ExploreDashboard:
                        help_msg = """
                        Use the metadata to explore your dataset with a dashboard
                        """
                        child = AssignMeta(self.goal, self)
                    else:
                        help_msg = """
                        Use GraphXplore to visually analyze and explore your data. The dataset will be stored in a 
                        graph database for efficient retrieval. Before exploring, you will have the option to define sub-groups 
                        within your dataset such as disease and control cohorts. For exploration, you can view the data as 
                        in various traditional plot forms, or use a graph-based visualization with *attribute association graphs*. 
                        GraphXplore identifies patterns of interest in your data and these graphs highlight associations of 
                        variables with groups, prevalence of attributes, and conditional dependencies with colors, shape sizes 
                        and visually clustering"""
                        child = AssignConnection(self)
                elif decision == 'Transform dataset':
                    help_msg = """
                    Use GraphXplore zu transform your dataset. You can split, combine and create new variables, or 
                    aggregate data such as time series. The transformation will be documented in a mapping JSON consisting 
                    of rules comprised of human-readable logical expressions for reuse or sharing with others. The mapping 
                    definition is solely based on metadata and can be defined without access to the actual data"""
                    child = AssignMeta(WorkflowGoal.TransformData, self)
                elif decision == 'Use metadata as is':
                    help_msg = """
                    GraphXplore will guide you through the mapping definition and data transformation with the metadata 
                    containing artifacts. You can either handle them in the mapping definition or incorporate them in 
                    the target dataset
                    """
                    child = AssignMeta(WorkflowGoal.TransformData, self)
                else:
                    raise NotImplementedError('Decision not implemented')

                help_col.markdown(help_msg)
                done_label = None
            else:
                child = AssignMeta(WorkflowGoal.TransformData, self)
                done_label = 'Proceed with transformation'
            self.render_mark_done(parent_obj, child, done_label)

class TriggerProcess(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask']=None):
        if goal == WorkflowGoal.ExtractMeta:
            header = 'Start Extraction'
        elif goal == WorkflowGoal.AddPrimaryKey:
            header = 'Generate New Table'
        elif goal == WorkflowGoal.CleanData:
            header = 'Start Data Cleaning'
        elif goal == WorkflowGoal.TransformData:
            header = 'Start Data Transformation'
        elif goal == WorkflowGoal.CreateBaseGraph:
            header = 'Start Base Graph Generation'
        elif goal == WorkflowGoal.ExploreDashboard:
            header = 'Start Dashboard Visualization'
        elif goal == WorkflowGoal.CreateAAG:
            header = 'Start Attribute Association Graph Generation'
        elif goal == WorkflowGoal.ExploreAAG:
            header = 'Retrieve AAG Table Data'
        else:
            raise NotImplementedError('Goal not implemented')
        super().__init__(header, goal, parent)

    def render(self, parent_obj):
        if self.goal == WorkflowGoal.ExtractMeta:
            msg = """
            - Choose level of artefact detection. If GraphXplore finds artefacts, these can be cleaned from your 
              dataset later
            - For advanced users: Define custom missing values and data type thresholds
            - Click on "Extract metadata" and wait for GraphXplore zu finish the extraction
            """
            child = ReviewMeta(self.goal, self)
            done = self.done_triggered
        elif self.goal == WorkflowGoal.AddPrimaryKey:
            msg = """
            - Optionally change primary key column name, starting integer, or the name of the new CSV table
            - Afterwards, click on "Generate new table"
            """
            child = FinishedAddPrimaryKey(self)
            done = ADD_PK_RESULT_DATA_KEY in st.session_state and len(st.session_state[ADD_PK_RESULT_DATA_KEY]) > 0
        elif self.goal == WorkflowGoal.CleanData:
            msg = """
            - Click on "Clean dataset"
            """
            done = (CLEAN_DATASET_RESULT_DATA_KEY in st.session_state
                    and len(st.session_state[CLEAN_DATASET_RESULT_DATA_KEY]) > 0)
            child = FinishCleanData(self)
        elif self.goal == WorkflowGoal.TransformData:
            msg = 'Click on "Transform data'
            done = TRANS_RESULT_DATA_KEY in st.session_state and len(st.session_state[TRANS_RESULT_DATA_KEY]) > 0
            child = FinishDataTransformation(self)
        elif self.goal == WorkflowGoal.CreateBaseGraph:
            msg = """
            - Select a database in which to store the generated base graph
                - Click in "Select Neo4J database for storage"
                - Choose between creating a new database (and inserting its name), or overwriting an existing database
                - Click on "Ok"
            - Optionally, adjust the missing values. Cells with these values will not be added to the base graph
            - Click on "Start graph generation" and wait for GraphXplore to finish the task. This might take a few 
              minutes. In the end, a success message will be displayed
            """
            done = self.done_triggered
            child = FinishedCreateBaseGraph(self)
        elif self.goal == WorkflowGoal.ExploreDashboard:
            msg = """
            - Choose between univariate or bivariate analysis. You can read more about these types of analysis in the 
              tooltip "Show dashboard tooltip"
                - For histogram plots you can choose between absolute count or fraction for the y-scale. Choosing 
                  fractions makes histograms comparable for imbalanced group sizes
            - Choose table(s) (if more than one table exists in your dataset), and variable(s) from the table(s) to plot
            - Click on "Query data for visualization"
            """
            done = self.done_triggered
            child = FinishedExploreDashboard(self)
        elif self.goal == WorkflowGoal.CreateAAG:
            msg = """
            - Select a database in which to store the generated attribute association graph
                - Click on "Select Neo4J database for storage of attribute association graph"
                - Choose between creating a new database (and inserting its name), or overwriting an existing database
                - Click on "Ok"
            - Optionally, adjust the advanced parameters. All functionalities have tooltips to help you
            - Click on "Start graph generation" and wait for GraphXplore to finish the task. This might take a few 
              minutes. In the end, a success message will be displayed
            """
            done = self.done_triggered
            child = FinishedCreateAGG(self)
        elif self.goal == WorkflowGoal.ExploreAAG:
            msg = """
            - Choose between viewing node or edge data in table form
            - Choose which metric to use for the ranking, the ranking order, and the number of results to retrieve
                - For group-level metrics, choose between the minimal or maximal value which should be used for the 
                  ranking
            - Select which parameters to display
            """
            done = self.done_triggered
            child = FinishedAAGTabularView(self)
        else:
            raise NotImplementedError('Goal not implemented')
        parent_obj.markdown(msg)

        if done and not self.done:
            self.render_mark_done(parent_obj, child)


class ReviewMeta(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask']=None):
        super().__init__('Review/Edit Metadata', goal, parent)

    def render(self, parent_obj):
        meta = st.session_state[MAIN_META_KEY]
        create_parent = isinstance(self.parent, CreateMeta)
        if create_parent:
            msg = """
            - Click on "View/Edit"
            - In the upper part of the page you can add tables
            - In the drop-down "Table-wide information" you can delete a table and add variables
            - When variables exist, you can delete them at the bottom of the page
            - You can use the "Variable filter" and "Table filter" (if your dataset has multiple tables) to only
              view a subset
            - All functionalities have tooltips and/or information when hovering over buttons or question marks
            - When you extracted the metadata and updated artifacts and/or variable or data types, you might want to 
              recalculate the value distribution
            - Optionally, you can mark variables as "reviewed" or "unreviewed" at the bottom right of the page
            """
        else:
            msg = """
            - Click on "View/Edit"
            - Inspect all variables, a subset thereof or fully trust GraphXplore
            - You can use the "Variable filter" and "Table filter" (if your dataset has multiple tables) to only
              view a subset
            - All functionalities have tooltips and/or information when hovering over buttons or question marks
            - Optionally, you can mark variables as "reviewed" or "unreviewed" at the bottom right of the page
            """
        parent_obj.markdown(msg)
        if not create_parent:
            if meta.has_artifacts():
                info_msg = """
                Metadata contains annotated artifacts. You can inspect them and de-select or leave them as is.  
                If artifacts remain after review, you will be asked if you want to clean your dataset in the next step
                """
                parent_obj.info(info_msg)
            else:
                parent_obj.info('Metadata has no annotated artifacts')
        done_label = None
        child = FinishedMeta(self.goal, self)
        tables_without_pk = []
        for table in meta.get_table_names():
            pk = meta.get_primary_key(table)
            if pk == '':
                tables_without_pk.append(table)
        if len(tables_without_pk) > 0:
            parent_obj.warning('The following table(s) have no primary key: "' + '", "'.join(tables_without_pk) + '"')
            if create_parent:
                pk_info_msg = """
                GraphXplore requires a primary key column for data exploration and transformation tasks. Consider to 
                assign them for the specified tables. In a dataset matching this metadata, all values in a primary key 
                column must be unique
                """
                parent_obj.info(pk_info_msg)
            else:
                pk_info_msg = """
                GraphXplore requires a primary key column for data exploration and transformation tasks. All values in a 
                primary key column must be unique. No such column was found in your dataset
                """
                parent_obj.info(pk_info_msg)
                radio_col, help_col = parent_obj.columns(2)
                pk_action = radio_col.radio('Do you want to add a primary key column?', ['Yes', 'No'])
                if pk_action == 'Yes':
                    help_msg = """
                    GraphXplore will help you to create a new dataset with a column containing unique values 
                    functioning as a primary key
                    """
                    done_label = 'Add primary key'
                    child = UploadData(WorkflowGoal.AddPrimaryKey, self)
                else:
                    help_msg = """
                    Leave your dataset as is. You will not be able to use GraphXplore for data exploration or 
                    transformation
                    """
                help_col.markdown(help_msg)

        self.render_mark_done(parent_obj, child, done_label)


class UploadData(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask']=None):
        header = 'Upload Data'
        if goal == WorkflowGoal.ExtractMeta:
            header += ' for Extraction'
        elif goal == WorkflowGoal.AddPrimaryKey:
            header += ' for Adding Primary Key'
        super().__init__(header, goal, parent)

    def render(self, parent_obj):
        if self.goal == WorkflowGoal.ExtractMeta:
            msg = """
            - Click on "Metadata" (in the sidebar)->"Select"->"Extract from Data"
            - Check delimiter (value seperator in CSV) and file encoding
            - Select all CSVs of your dataset via drag and drop, or "Browse files"
            - Click "Upload data"
            """
            parent_obj.markdown(msg)
            done = META_EXTRACT_DATA_KEY in st.session_state and len(st.session_state[META_EXTRACT_DATA_KEY]) > 0
        elif self.goal == WorkflowGoal.AddPrimaryKey:
            msg = """
            - Click on "Data Transformation" (in the sidebar)->"Utility"->"Add primary key"
            - Check delimiter (value seperator in CSV) and file encoding
            - Select a single CSV file via drag and drop, or "Browse files"
            - Click "Upload data"
            """
            parent_obj.markdown(msg)
            done = ADD_PK_SOURCE_DATA_KEY in st.session_state and len(st.session_state[ADD_PK_SOURCE_DATA_KEY]) > 0
        elif self.goal == WorkflowGoal.CleanData:
            msg = """
            - Check delimiter (value seperator in CSV) and file encoding
            - Select all CSVs of your dataset via drag and drop, or "Browse files"
            - Click "Upload data"
            """
            parent_obj.markdown(msg)
            done = (CLEAN_DATASET_SOURCE_DATA_KEY in st.session_state
                    and len(st.session_state[CLEAN_DATASET_SOURCE_DATA_KEY]) > 0)
        elif self.goal == WorkflowGoal.TransformData:
            msg = """
            - Click on "Data Transformation" (tab to the right, not in the sidebar)
            - Check delimiter (value seperator in CSV) and file encoding
            - Select all CSVs of your dataset via drag and drop, or "Browse files"
            - Click "Upload data"
            """
            parent_obj.markdown(msg)
            done = TRANS_SOURCE_DATA_KEY in st.session_state and len(st.session_state[TRANS_SOURCE_DATA_KEY]) > 0
        elif self.goal == WorkflowGoal.CreateBaseGraph:
            msg = """
            - Check delimiter (value seperator in CSV) and file encoding
            - Select all CSVs of your dataset via drag and drop, or "Browse files"
            - Click "Upload data"
            """
            parent_obj.markdown(msg)
            done = TRANSLATION_SOURCE_DATA_KEY in st.session_state and len(st.session_state[TRANSLATION_SOURCE_DATA_KEY]) > 0
        else:
            raise NotImplementedError('Upload data for this goal not implemented')

        if done:
            self.render_mark_done(parent_obj, TriggerProcess(self.goal, self))

class ChooseMetaSource(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask'] = None):
        super().__init__('Choose Metadata Source', goal, parent)

    def render(self, parent_obj):
        parent_obj.markdown('All workflows in GraphXplore require metadata')
        radio_col, help_col = parent_obj.columns(2)
        if MAIN_META_KEY in st.session_state and st.session_state[MAIN_META_KEY] is not None:
            options = ['Use selected metadata', 'Load existing metadata', 'Extract metadata from dataset']
        else:
            options = ['Load existing metadata', 'Extract metadata from dataset']
        if self.goal == WorkflowGoal.TransformData:
            options.append('Create metadata from scratch')
        meta_opt = radio_col.radio('Choose metadata source', options)
        if meta_opt == 'Use selected metadata':
            help_msg = """
            You already have selected metadata before. You can reuse it here
            """
            child = ReviewMeta(self.goal, self)
        elif meta_opt == 'Load existing metadata':
            help_msg = """
            You already have metadata for your exact dataset. GraphXplore will load it from a JSON file and you can use 
            it in your workflow
            """
            child = LoadMeta(self.goal, self)
        elif meta_opt == 'Extract metadata from dataset':
            help_msg = """
            GraphXplore will generate metadata of your dataset by extracting variables, data types, 
            distributions, artifacts and primary/foreign key relations. You can review and adjust the extracted 
            information, add variable tags or descriptions, and annotate special or missing values as artifacts. 
            Afterwards, you can use the extracted metadata for sharing or in other GraphXplore workflows"""
            child = UploadData(WorkflowGoal.ExtractMeta, self)
        else:
            help_msg = """
            Create a completely new metadata for which no dataset exists yet. You will have to define each table, 
            variable, and primary/foreign key relation manually. If you already have metadata of which you can reuse 
            some tables and/or variables, you can choose "Load existing metadata" and edit it to you needs afterwards. 
            When completed, you can use the created metadata in your GraphXplore workflow"""
            child = CreateMeta(self.goal, self)
        help_col.markdown(help_msg)
        self.render_mark_done(parent_obj, child)

class LoadMeta(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask'] = None):
        super().__init__('Load Metadata', goal, parent)

    def render(self, parent_obj):
        msg = """
        - Click on "Metadata" (in the sidebar)->"Select"->"Load from JSON"
        - Click on "Browse files" and select your metadata JSON  file, or drag and drop the metadata JSON file into the 
          widget
        - Optionally specify the file encoding. By default it will be automatically detected
        - Click on "Load metadata" and wait for GraphXplore to load the metadata
        """
        parent_obj.markdown(msg)
        if MAIN_META_KEY in st.session_state and st.session_state[MAIN_META_KEY]:
            if self.goal in [WorkflowGoal.ExploreDashboard, WorkflowGoal.ExploreAAG, WorkflowGoal.DefineGroup,
                             WorkflowGoal.CreateBaseGraph]:
                child = AssignMeta(self.goal, self)
            else:
                child = ReviewMeta(self.goal, self)
            self.render_mark_done(parent_obj, child)


class AssignMeta(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask'] = None):
        super().__init__('Assign Metadata', goal, parent)

    def render(self, parent_obj):
        if self.goal == WorkflowGoal.CleanData:
            msg = """
            - Click on "Data Transformation" (in the sidebar)->"Utility"->"Clean dataset"
            - Click on "Assign metadata"
            """
            done = CLEAN_DATASET_META_KEY in st.session_state and st.session_state[CLEAN_DATASET_META_KEY]
            child = UploadData(self.goal, self)
        elif self.goal == WorkflowGoal.ExploreDashboard:
           msg = """
           - Click on "Data Exploration" (in the sidebar)->"DataExploration"->"Dataset Dashboard"
           - Click on "Assign metadata"
           """
           child = ChooseInputDB(self.goal, self)
           done = DASHBOARD_META_KEY in st.session_state and st.session_state[DASHBOARD_META_KEY]
        elif self.goal == WorkflowGoal.CreateAAG:
           msg = """
           - Click on "Data Exploration" (in the sidebar)->"Graph Generation"->"Attribute Association Graph Generation"
           - Click on "Assign selected metadata"
           """
           child = ChooseInputDB(self.goal, self)
           done = AAG_META_KEY in st.session_state and st.session_state[AAG_META_KEY]
        elif self.goal == WorkflowGoal.CreateBaseGraph:
            msg = """
            - Click on "Data Exploration" (in the sidebar)->"Graph Generation"->"Base Graph Generation"
            - Click on "Assign metadata"
            """
            done = TRANSLATION_META_KEY in st.session_state and st.session_state[TRANSLATION_META_KEY]
            child = UploadData(self.goal, self)
        elif self.goal == WorkflowGoal.TransformData:
            if self.get_source_target_suffix(True) in self.header:
                msg_assign = 'Source'
                done = SOURCE_META_KEY in st.session_state and st.session_state[SOURCE_META_KEY]
            elif self.get_source_target_suffix(False) in self.header:
                msg_assign = 'Target'
                done = TARGET_META_KEY in st.session_state and st.session_state[TARGET_META_KEY]
            else:
                msg_assign = 'Source or Target'
                done = ((SOURCE_META_KEY in st.session_state and st.session_state[SOURCE_META_KEY])
                        or (TARGET_META_KEY in st.session_state and st.session_state[TARGET_META_KEY]))
            msg = f"""
            - Click on "Data Transformation" (in the sidebar)->""Data Mapping"->"Metadata assignment"
            - Choose {msg_assign}
            - If a you already selected a mapping before, you will have to check the box for resetting the existing 
              mapping (Before, you can store the selected other mapping at "Store") 
            - Click on "Assign"
            """
            child = TransformationMetaProcess(self)
        else:
            raise NotImplementedError('Goal not implemented')
        parent_obj.markdown(msg)
        if done:
            self.render_mark_done(parent_obj, child)

class FinishedAddPrimaryKey(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finish Adding Primary Key', WorkflowGoal.AddPrimaryKey, parent)

    def render(self, parent_obj):
        msg = """
        - You added a primary key to your CSV table :tada:
        - You can store the newly generated table by clicking on "Store generated table". Optionally, you can 
          adjust the file encoding and the CSV delimiter
        - You can use the stored table in other GraphXplore workflows"""
        parent_obj.markdown(msg)
        if not self.done:
            dec_col, help_col = parent_obj.columns(2)
            options = ['Extract New Metadata', 'Add Primary Key to Other Table', 'Finish workflow']
            decision = dec_col.radio('How do you want to proceed?', options, key=self.widget_key_stem + '_proceed')
            if decision == 'Extract New Metadata':
                help_msg = """
                Extract metadata of you dataset containing the newly generated table with added primary key. After 
                reviewing, you can use this dataset and metadata for other GraphXplore workflows
                """
                child = UploadData(WorkflowGoal.ExtractMeta, self)
            elif decision == 'Finish workflow':
                help_msg = """
                You are done with the workflow and GraphXplore will stop guiding you for now. If you want to start a 
                new workflow, you can do so at any time
                """
                child = None
            else:
                help_msg = """
                Another CSV table of your dataset does not have a primary key column yet? You can repeat the last steps 
                for this table as well
                """
                child = UploadData(WorkflowGoal.AddPrimaryKey, self)
            help_col.markdown(help_msg)
            self.render_mark_done(parent_obj, child)

class FinishCleanData(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finish Data Cleaning', WorkflowGoal.CleanData, parent)

    def render(self, parent_obj):
        msg = """
        - You cleaned your dataset :tada:
        - You can store the cleaned dataset by clicking on "Store cleaned dataset". Optionally, you can 
          adjust the file encoding and the CSV delimiter
        - You can use the stored table in other GraphXplore workflows"""
        parent_obj.markdown(msg)
        if not self.done:
            dec_col, help_col = parent_obj.columns(2)
            options = ['Extract New Metadata', 'Finish workflow']
            decision = dec_col.radio('How do you want to proceed?', options, key=self.widget_key_stem + '_proceed')
            if decision == 'Extract New Metadata':
                help_msg = """
                Extract metadata of you cleaned dataset After reviewing, you can use this dataset and metadata for 
                other GraphXplore workflows
                """
                child = UploadData(WorkflowGoal.ExtractMeta, self)
            else:
                help_msg = """
                You are done with the workflow and GraphXplore will stop guiding you for now. If you want to start a 
                new workflow, you can do so at any time
                """
                child = None
            help_col.markdown(help_msg)
            self.render_mark_done(parent_obj, child)

class CreateMeta(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask'] = None):
        super().__init__('Create Metadata', goal, parent)

    def render(self, parent_obj):
        msg = """
        - Click on "Metadata" (in the sidebar)->"Select"->"Create from Scratch"
        - Click on the drop-down "Table names" and add one or multiple table names. You can add/remove tables later
        - Click on "Create metadata"
        """
        parent_obj.markdown(msg)
        if MAIN_META_KEY in st.session_state and st.session_state[MAIN_META_KEY]:
            self.render_mark_done(parent_obj, ReviewMeta(self.goal, self))

class TransformationMetaProcess(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Metadata Process for Transformation', WorkflowGoal.TransformData, parent,
                         add_source_target_suffix=False)

    def render(self, parent_obj):
        msg = """
        - A transformation workflow in GraphXplore starts with metadata for the source and target of the transformation
        - For both the source and target, you can load the metadata, extract it from an existing dataset or create it 
          from scratch
        """
        parent_obj.markdown(msg)
        if not self.done:
            source_assigned = SOURCE_META_KEY in st.session_state and st.session_state[SOURCE_META_KEY]
            target_assigned = TARGET_META_KEY in st.session_state and st.session_state[TARGET_META_KEY]
            options = ['Select source metadata', 'Select target metadata']
            idx = 1 if source_assigned else 0
            if source_assigned and target_assigned:
                options = ['Both metadata selections seem fine'] + options
                idx = 0
            radio_col, help_col = parent_obj.columns(2)
            option = radio_col.radio('How do you want to proceed?', options, index=idx)
            if option == 'Both metadata selections seem fine':
                child = SelectMapping(self)
                help_msg = """
                The source and target both have assigned metadata. You are ready to start with the mapping definition and a 
                potential data transformation
                """
            else:
                meta_type = 'source' if option == 'Select source metadata' else 'target'
                help_msg = f"""
                Load, extract or create metadata for the {meta_type}
                """
                child = ChooseMetaSource(self.goal, self)

                child.header += (self.get_source_target_suffix(True) if option == 'Select source metadata'
                                 else self.get_source_target_suffix(False))
            help_col.markdown(help_msg)
            self.render_mark_done(parent_obj, child)

class SelectMapping(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Select Mapping', WorkflowGoal.TransformData, parent)

    def render(self, parent_obj):
        msg = """
        - Under the header "Mapping" click on "Select"
        """
        parent_obj.markdown(msg)
        select_opt = parent_obj.radio('Choose how to select mapping', ['Load existing mapping', 'Create new mapping'],
                                      disabled=self.done)
        if select_opt == 'Load existing mapping':
            other_msg = """
            - Click on "Load from JSON"
            - drag and drop your mapping JSON or click on "Browse files"
            - Optionally, adjust the file encoding
            - Click on "Load mapping"
            """
        else:
            other_msg = """
            - Click on "Create new mapping"
            - Choose one of the options
            - Click on "Create mapping"
            """
        parent_obj.markdown(other_msg)
        if MAIN_MAPPING_KEY in st.session_state and st.session_state[MAIN_MAPPING_KEY]:
            self.render_mark_done(parent_obj, ReviewMapping(self))

class ReviewMapping(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Review/Edit Mapping', WorkflowGoal.TransformData, parent)

    def render(self, parent_obj):
        msg = """
        - Click on "View/Edit"
        - All functionalities have tooltips and/or information when hovering over buttons or question marks. The 
          tooltip at the top of the page gives a general overview how data mappings work in GraphXplore
        - If not yet present, you first have to assign a table mapping for each table of the target dataset. 
          Optionally, you can add a condition to only use a subset of the source data
        - You can define new mapping cases by clicking on the drop-down "New mapping case"
        - Below the subheader "Mapping" you can see, if your mapping is complete (all target variables are mapped), or 
          how many variables are still unmapped. By clicking on "Show only target tables with unmapped variables" and/or 
          "Show only unmapped target variables", you can filter your mapping view to tables and variables that still 
          need mapping definition
        - You can always store the mapping in an unfinished form and proceed at a later 
          time. To do this, click on "Store"->"Store mapping"
        """
        parent_obj.markdown(msg)
        mapping = st.session_state[MAIN_MAPPING_KEY]
        if mapping.complete():
            parent_obj.success('Mapping complete')
        else:
            parent_obj.info('Some table and/or variable mappings are still missing')
        self.render_mark_done(parent_obj, FinishMapping(self))

class FinishMapping(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finish Mapping', WorkflowGoal.TransformData, parent)

    def render(self, parent_obj):
        msg = """
        - You finished the data mapping inspection :tada:
        - You can store the mapping in its current form at "Store"->"Store mapping". Optionally you can 
          adjust the file encoding
        - Completed mappings with all table and variable mappings defined can be used for data transformation with 
          GraphXplore
        """
        parent_obj.markdown(msg)
        if not self.done:
            mapping = st.session_state[MAIN_MAPPING_KEY]
            if mapping.complete():
                radio_col, help_col = parent_obj.columns(2)
                decision = radio_col.radio('How do you want to proceed?', ['Transform dataset', 'Finish workflow'])
                if decision == 'Transform dataset':
                    help_msg = """
                    Use this data mapping to create a new target dataset based on your source dataset. You can use the 
                    newly generated target dataset in other GraphXplore workflows
                    """
                    child = UploadData(WorkflowGoal.TransformData, self)
                else:
                    help_msg = """
                    You are done with the workflow and GraphXplore will stop guiding you for now. If you want to start 
                    a new workflow, you can do so at any time
                    """
                    child = None
                help_col.markdown(help_msg)
            else:
                parent_obj.info('Some table(s) and/or variable(s) are still unmapped. Therefore, you cannot use the '
                                'mapping in its current form for data transformation. But you can always proceed with '
                                'the mapping definition at a later time')
                child = None
            self.render_mark_done(parent_obj, child)

class FinishDataTransformation(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finish Data Transformation', WorkflowGoal.TransformData, parent)

    def render(self, parent_obj):
        msg = """
        - You finished the data transformation :tada:
        - Store the newly generated target dataset by clicking on "Store transformed data". Optionally you can 
          adjust the file encoding and CSV delimiter
        - You can use the new dataset in other GraphXplore workflows GraphXplore
        """
        parent_obj.markdown(msg)
        if not self.done:
            radio_col, help_col = parent_obj.columns(2)

            selection = radio_col.radio('How do you want to proceed?', ['Extract Metadata', 'Explore Dataset',
                                                                        'Finish Workflow'])

            if selection == 'Extract Metadata':
                help_msg = """
                You already defined metadata of your target dataset. However, artifact detection and calculation of 
                value distributions might still be useful insights into your new dataset. Use GraphXplore to extract 
                metadata of your newly created dataset
                """
                child = UploadData(WorkflowGoal.ExtractMeta, self)
            elif selection == 'Explore Dataset':
                help_msg = """
                Use GraphXplore to visually analyze and explore your newly created dataset. The dataset will be stored in a 
                graph database for efficient retrieval. Before exploring, you will have the option to define sub-groups 
                within your dataset such as disease and control cohorts. For exploration, you can view the data with 
                various traditional plots, or use a graph-based visualization with *attribute association graphs*. 
                GraphXplore identifies patterns of interest in your data and these graphs highlight associations of 
                variables with groups, prevalence of attributes, and conditional dependencies with colors, shape sizes 
                and visually clustering
                """
                child = ChooseMetaSource(WorkflowGoal.ExploreData)
            else:
                help_msg = """
                You are done with the workflow and GraphXplore will stop guiding you for now. If you want to start 
                a new workflow, you can do so at any time
                """
                child = None

            help_col.markdown(help_msg)
            self.render_mark_done(parent_obj, child)

class AssignConnection(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Connect to Neo4J', WorkflowGoal.ExploreData, parent)

    def render(self, parent_obj):
        msg = """
        All data exploration in GraphXplore is based on the database management system Neo4J
        - Start your local or remote Neo4J DBMS
        - Click on "Data Exploration" (in the sidebar)-> "Assign connection to Neo4J database management system"
        - Optionally adjust the server host and port
        - Fill in the correct username and password, if authentication is required for your Neo4J DBMS
        - Click on "Assign connection"
        - Keep the connection to the Neo4J alive during your whole data exploration workflow
        """
        parent_obj.markdown(msg)
        if not self.done:
            done = (NEO4J_ADDRESS_KEY in st.session_state and st.session_state[NEO4J_ADDRESS_KEY] is not None
                    and NEO4J_AUTH_KEY in st.session_state and st.session_state[NEO4J_AUTH_KEY] is not None)
            if done:
                self.render_mark_done(parent_obj, ChooseExploration(self))

class ChooseExploration(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Choose Exploration Type', WorkflowGoal.ExploreData, parent)

    def render(self, parent_obj):
        radio_col, help_col = parent_obj.columns(2)
        selection = radio_col.radio('How would you like to explore your data?', ['Graph-based', 'Dashboard'])
        if selection == 'Graph-based':
            help_msg = """
            Explore your data with *attribute association graphs*. These graphs use simple statistical metrics and 
            highlight associations of variables with groups, prevalence of attributes, and conditional dependencies 
            with colors, shape sizes and visually clustering. To read more about them, go to "Data Exploration" (in the 
            sidebar)-> "Data Exploration" -> "Intro to Attribute Association Graphs"
            """
            aag_radio_col, aag_help_col = parent_obj.columns(2)
            aag_selection = aag_radio_col.radio(
                'Did you already generate an attribute association graph for your use case?', ['Yes', 'No'])
            if aag_selection == 'Yes':
                aag_help_msg = """
                You already generated an attribute association graph and are ready for exploration!
                """
                child = ChooseAAGView(self)
            else:
                aag_help_msg = """
                You have no attribute association graph available for your use case yet. In the next steps, GraphXplore 
                will guide you to generate one
                """
                child = CheckBaseGraph(WorkflowGoal.CreateAAG, self)
            aag_help_col.markdown(aag_help_msg)

        else:
            help_msg = """
            Use histogram and scatter plots, or pie and bar charts to explore distributions within 
            your data. Additionally, you can define groups within your data to fine-tune your plots and compare results 
            between groups
            """
            child = CheckBaseGraph(WorkflowGoal.ExploreDashboard, self)
        help_col.markdown(help_msg)
        parent_obj.markdown('If you want to explore both visualizations, you can always come back here or start a new workflow')
        if not self.done:
            self.render_mark_done(parent_obj, child)

class ChooseAAGView(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Choose AAG View', WorkflowGoal.ExploreAAG, parent)

    def render(self, parent_obj):
        main_msg = """
        You can explore your attribute association graph visually directly in graph form, or in tabular form.
        """
        parent_obj.markdown(main_msg)
        radio_col, help_col = parent_obj.columns(2)
        selection = radio_col.radio('How would you like to explore your data?', ['Graph-based', 'Table'])
        if selection == 'Graph-based':
            help_msg = """
            Visually explore your graph. Associations of variables with groups, prevalence of attributes, and 
            conditional dependencies are highlighted with colors, shape sizes and visually clustering. In the next step 
            you can read a user guide for the visual exploration in Neo4J and detailed information on all statistical 
            metrics used
            """
            child = ReadAAGIntro(self)
        else:
            help_msg = """
            Statistical metrics and meta information of the nodes and edges of the graph will be retrieved and 
            presented in tabular form. GraphXplore will assist you in filtering and sorting the results. This 
            table-based representation omits the visual exploration aspect of the graph, but can be useful in later 
            stages of your project for documenting your results, or transferring them to another tool 
            """
            child = ChooseInputDB(WorkflowGoal.ExploreAAG, self)
        help_col.markdown(help_msg)
        if not self.done:
            self.render_mark_done(parent_obj, child)


class CheckBaseGraph(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask'] = None):
        super().__init__('Check Base Graph', goal, parent)

    def render(self, parent_obj):
        msg = """
        Data exploration in GraphXplore builds on graph databases in Neo4J. Therefore, you dataset has to be converted 
        and loaded into such a graph database. Deduplicated triples of table, variable and cell value will be stored as 
        nodes in the database. Nodes of primary key values will be connected via edges to nodes of the other cell 
        values in their row. This data format allows GraphXplore to efficiently query your data and even perform 
        complex table joins. The result is called a :red[base graph]
        """
        parent_obj.markdown(msg)
        radio_col, help_col = parent_obj.columns(2)
        selection = radio_col.radio('Did you already convert your dataset into a base graph?', ['Yes', 'No'])
        if selection == 'Yes':
            help_msg = """
            You can directly use your generated base graph for your workflow
            """
            if MAIN_META_KEY in st.session_state and st.session_state[MAIN_META_KEY] is not None:
                child = AssignMeta(self.goal, self)
            else:
                child = LoadMeta(self.goal, self)
        else:
            help_msg = """
            GraphXplore will guide you to convert your dataset into a graph database. You can use the generated base 
            graph for all your future exploration tasks on this dataset
            """
            if MAIN_META_KEY in st.session_state and st.session_state[MAIN_META_KEY] is not None:
                child = AssignMeta(WorkflowGoal.CreateBaseGraph, self)
            else:
                meta_radio_col, meta_help_col = parent_obj.columns(2)
                meta_selection = meta_radio_col.radio(
                    'Do you already have extracted metadata for your dataset?', ['Yes', 'No'])
                if meta_selection == 'Yes':
                    meta_help_msg = """
                    You already have extracted and reviewed metadata for your dataset with GraphXplore. In the next 
                    step you can load and can use it to generate the base graph
                    """
                    child = LoadMeta(WorkflowGoal.CreateBaseGraph, self)
                else:
                    meta_help_msg = """
                    You have not extracted metadata for your dataset yet. In the next steps, GraphXplore will guide you 
                    through extracting metadata, reviewing key relations, data types and artifacts. Afterwards, you can 
                    use the generated metadata for all future GraphXplore workflows
                    """
                    child = UploadData(WorkflowGoal.ExtractMeta, self)
                meta_help_col.markdown(meta_help_msg)

        help_col.markdown(help_msg)
        if not self.done:
            self.render_mark_done(parent_obj, child)

class FinishedCreateBaseGraph(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finish Base Graph Creation', WorkflowGoal.CreateBaseGraph, parent)

    def render(self, parent_obj):
        msg = """
        You converted your dataset into a base graph :tada:. You can use this base graph for all future exploration 
        workflows in GraphXplore!
        """
        parent_obj.markdown(msg)
        radio_col, help_col = parent_obj.columns(2)
        selection = radio_col.radio(
            'How do you want to proceed', ['Create Attribute Association Graph', 'Explore Base Graph with Dashboard',
                                           'Finish Workflow'])
        if selection == 'Create Attribute Association Graph':
            help_msg = """
            GraphXplore will guide you to create an *attribute association graph* of your dataset. These graphs use 
            simple statistical metrics and highlight associations of variables with groups, prevalence of attributes, 
            and conditional dependencies with colors, shape sizes and visually clustering. To read more about them, go 
            to "Data Exploration" (in the sidebar)-> "Data Exploration" -> "Intro to Attribute Association Graphs"
            """
            child = AssignMeta(WorkflowGoal.CreateAAG, self)
        elif selection == 'Explore Base Graph with Dashboard':
            help_msg = """
            You are ready to explore distributions within your dataset with traditional plots. Additionally, you can 
            define groups within your data to fine-tune your plots and compare results 
            between groups
            """
            child = AssignMeta(WorkflowGoal.ExploreDashboard, self)
        else:
            help_msg = """
            You are done with the workflow and GraphXplore will stop guiding you for now. If you want to start a new 
            workflow, you can do so at any time
            """
            child = None
        help_col.markdown(help_msg)
        if not self.done:
            self.render_mark_done(parent_obj, child)

class ChooseInputDB(Subtask):
    def __init__(self, goal: WorkflowGoal, parent: Optional['Subtask'] = None):
        if goal in [WorkflowGoal.ExploreDashboard, WorkflowGoal.CreateAAG]:
            header = 'Select Base Graph Database'
        elif goal == WorkflowGoal.ExploreAAG:
            header = 'Select AAG Database'
        else:
            raise NotImplementedError('Goal not implemented')
        super().__init__(header, goal, parent)

    def render(self, parent_obj):
        if self.goal in [WorkflowGoal.ExploreDashboard, WorkflowGoal.CreateAAG]:
            msg = """
            - Click on "Select Neo4J base graph database for data retrieval"
            - Choose a database containing a base graph matching your metadata
            - Click on "Ok"
            """
            if self.goal == WorkflowGoal.ExploreDashboard:
                done = DASHBOARD_DB_KEY in st.session_state and st.session_state[DASHBOARD_DB_KEY] is not None
                child = DefineDashboardBasis(self)
            else:
                done = AAG_INPUT_DB_KEY in st.session_state and st.session_state[AAG_INPUT_DB_KEY] is not None
                child = AAGSelectGroups(self)
        elif self.goal == WorkflowGoal.ExploreAAG:
            msg = """
            - Click on "Data Exploration (side bar)->"Data Exploration"->"Attribute Association Graph Tabular View"
            - Click on "Select Neo4J database for attribute association graph tabular view
            - Choose a database containing an attribute association graph
            - Click on "Ok"
            """
            done = AAG_TABLE_DB_KEY in st.session_state and st.session_state[AAG_TABLE_DB_KEY] is not None
            child = TriggerProcess(WorkflowGoal.ExploreAAG, self)
        else:
            raise NotImplementedError('Goal not implemented')

        parent_obj.markdown(msg)

        if done and not self.done:
            self.render_mark_done(parent_obj, child)

class DefineDashboardBasis(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Define Dashboard Basis', WorkflowGoal.ExploreDashboard, parent)

    def render(self, parent_obj):
        msg = """
        - Choose one of the tables of your dataset as the basis of your visualization. The primary key values of this 
          table will form the basis of the plots. You will be able to pick any variable of 
          this table or any foreign table for your plots (primary and foreign keys are excluded)
        - Optionally, you can add groups of this table that you defined in "Group Definitions"
        """
        parent_obj.markdown(msg)
        child = TriggerProcess(self.goal, self)
        done = DASHBOARD_BASIS_TABLE in st.session_state and st.session_state[DASHBOARD_BASIS_TABLE] is not None
        if DEFINED_GROUP_KEY not in st.session_state or len(st.session_state[DEFINED_GROUP_KEY]) == 0:
            radio_col, help_col = parent_obj.columns(2)
            selection = radio_col.radio(
                'You have no defined groups to select yet. Do you want to load or create groups?', ['Yes', 'No'])
            if selection == 'Yes':
                help_msg = """
                GraphXplore will guide you in creating subgroups such ans disease and control cohorts of your dataset. 
                You will be able to store, reload and reuse these groups for both the dashboard and graph-based data 
                visualization
                """
                child = DefineGroupsStart(self)
                done = True
            else:
                help_msg = """
                Proceed without defining groups. The plots will show data points for all primary keys of your basis 
                table. If you like to define groups at a later stage, you can come back here at any time or start a new 
                workflow
                """
            help_col.markdown(help_msg)

        if done and not self.done:
            self.render_mark_done(parent_obj, child)

class FinishedExploreDashboard(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finish Dashboard Exploration', WorkflowGoal.CreateBaseGraph, parent)

    def render(self, parent_obj):
        msg = """
        You generated a dashboard to explore your dataset :tada:
        - You can select/deselect items in the legend to focus the plot on certain groups or categorical values
        - You can store your plots as PNG file
        - You can choose another plot type and/or other variables to plot
        - If you want to proceed with a graph-based data visualization, you can start a new workflow below
        """
        parent_obj.markdown(msg)
        if not self.done:
            self.render_mark_done(parent_obj, None)

class DefineGroupsStart(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Start Group Definition', WorkflowGoal.DefineGroup, parent)

    def render(self, parent_obj):
        msg = """
        In GraphXplore, you can define groups of primary key values to fine-tune your data exploration. Groups have a 
        name, a table of origin, and a condition defined by a logical expression. All primary key values that meet the 
        defined condition, get added to the group
        """
        parent_obj.markdown(msg)
        radio_col, help_col = parent_obj.columns(2)
        selection = radio_col.radio(
            'You do you want to proceed?', ['Create new groups', 'Load pre-defined groups'])
        if selection == 'Create new groups':
            help_msg = """
            In the next step you can create one or multiple groups of your dataset with the adequate conditions for 
            your use case
            """
            child = CreateGroup(self)
        else:
            help_msg = """
            You already defined groups for your dataset und can load them now for usage in your exploration workflow
            """
            child = LoadGroups(self)
        help_col.markdown(help_msg)
        if not self.done:
            self.render_mark_done(parent_obj, child)

class CreateGroup(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Define Group', WorkflowGoal.DefineGroup, parent)
        self.group_name = None

    def render(self, parent_obj):
        meta_assigned = GROUP_META_KEY in st.session_state and st.session_state[GROUP_META_KEY]
        group_created = (self.group_name is not None
                         and DEFINED_GROUP_KEY in st.session_state
                         and self.group_name in st.session_state[DEFINED_GROUP_KEY])
        msg = f"""
        Click on "Group Definitions"->"View/edit groups"->"Define new group":
        - Assign your selected metadata by clicking on "Assign selected metadata" {':heavy_check_mark:' if meta_assigned else ''}
            - If you did not select metadata before, load, extract or create it by clicking on "Metadata" in the 
              sidebar or choose a suitable workflow
        - Insert a group name, choose table of origin for the group members, and decide on the group condition. Then 
          click on "Create new group" {':heavy_check_mark:' if group_created else ''}
            - You can either incorporate all primary key values of the group table, or filter them with a logical 
              expression. While building the logical expression, you can always hover over the question mark to get help
        """
        parent_obj.markdown(msg)
        if not self.done and group_created:
            create_another_col, done_col = parent_obj.columns(2)
            self.render_mark_done(create_another_col, CreateGroup(self), button_label='Define another group')
            self.render_mark_done(done_col, FinishedGroupDefinition(self), button_label='Finished all groups')

class LoadGroups(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Load Group Definitions', WorkflowGoal.DefineGroup, parent)

    def render(self, parent_obj):
        meta_assigned = GROUP_LOAD_META in st.session_state and st.session_state[GROUP_LOAD_META]
        msg = f"""
        To load pre-defined group definitions at "Group Definitions"->"Load groups from JSON":
        - Assign your selected metadata by clicking on "Assign selected metadata" {':heavy_check_mark:' if meta_assigned else ''}
            - If you did not select metadata before, load, extract or create it by clicking on "Metadata" in the 
              sidebar or choose a suitable workflow
        - Upload you group definitions matching the metadata via drag and drop or by clicking on "Browse files" and 
          click on "Load groups" {' :heavy_check_mark:' if self.done_triggered else ''}
        """
        parent_obj.markdown(msg)
        if self.done_triggered and not self.done:
            self.render_mark_done(parent_obj, FinishedGroupDefinition(self))

class FinishedGroupDefinition(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finished Group Definitions', WorkflowGoal.DefineGroup, parent)

    def render(self, parent_obj):
        msg = """
        You finished the group definition workflow :tada:
        - Your group definitions will remain until you overwrite them with other definitions or close GraphXplore
        - You can store all or a subset definitions of one dataset in a JSON at "Store groups"
            - Choose one or multiple groups by name
            - Click on "Store groups"
        """
        parent_obj.markdown(msg)
        radio_col, help_col = parent_obj.columns(2)
        selection = radio_col.radio(
            'You do you want to proceed?', [
                'Use groups for dashboard', 'Use groups for attribute association graph generation','Finish workflow'
            ])
        if selection == 'Finish workflow':
            help_msg = """
            You are done with the workflow and GraphXplore will stop guiding you for now. If you want to start a new 
            workflow, you can do so at any time
            """
            child = None
        elif selection == 'Use groups for dashboard':
            help_msg = """
            Start or proceed with your data exploration workflow based on a dashboard. You can incorporate your defined 
            groups to fine-tune your exploration
            """
            if DASHBOARD_DB_KEY in st.session_state and st.session_state[DASHBOARD_DB_KEY] is not None:
                child = DefineDashboardBasis(self)
            else:
                child = CheckBaseGraph(WorkflowGoal.ExploreDashboard, self)
        else:
            help_msg = """
            Start or proceed with the generation of an attribute association graph. Distributions of variables within 
            your defined groups will be analyzed and highlighted
            """
            child = AAGSelectGroups(self)

        help_col.markdown(help_msg)

        if not self.done:
            self.render_mark_done(parent_obj, child)


class AAGSelectGroups(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Select Groups', WorkflowGoal.CreateAAG, parent)

    def render(self, parent_obj):
        if DEFINED_GROUP_KEY not in st.session_state or len(st.session_state[DEFINED_GROUP_KEY]) == 0:
            msg = """
            You have no defined groups to select yet. GraphXplore will guide you to either create new groups or load 
            pre-defined ones
            """
            parent_obj.markdown(msg)
            child = DefineGroupsStart(self)
            done = True
        else:
            selection = parent_obj.radio(
                'You have defined groups that you can select here. Are these the correct groups, or do you have to '
                'create or load additional groups?', ['Use existing', 'Create/load new groups'])
            if selection == 'Use existing':
                msg = """
                - Choose groups to add to your selection
                - Optionally, assign group distinctions. You must assign both the positive and negative group, or none 
                  of them. For more information, check out the group distinction tooltip
                """
                parent_obj.markdown(msg)
                done = AAG_CHOSEN_GROUPS in st.session_state and len(st.session_state[AAG_CHOSEN_GROUPS]) > 0
                if (len(st.session_state[AAG_CHOSEN_GROUPS]) >= 2
                        and (st.session_state[AAG_POS_GROUP] is None or st.session_state[AAG_NEG_GROUP] is None)):
                    parent_obj.info('You have selected at least two groups, but did not fully assign group distinctions. '
                                    'Distinctions greatly increase the potential to visually highlight patterns of '
                                    'interest')
                child = TriggerProcess(self.goal, self)
            else:
                child = DefineGroupsStart(self)
                done = True

        if done and not self.done:
            self.render_mark_done(parent_obj, child)

class FinishedCreateAGG(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finished AAG Creation', WorkflowGoal.CreateAAG, parent)

    def render(self, parent_obj):
        msg = """
        You finished the attribute association graph creation :tada:
        - The created graph is stored as a Neo4J database and can be accessed any time
        - You can explore the whole graph visually using Neo4J functionalities, or retrieve data in tabular form
        """
        parent_obj.markdown(msg)
        radio_col, help_col = parent_obj.columns(2)
        selection = radio_col.radio(
            'You do you want to proceed?', [
                'Explore attribute association graph', 'Finish workflow'
            ])
        if selection == 'Finish workflow':
            help_msg = """
            You are done with the workflow and GraphXplore will stop guiding you for now. If you want to start a new 
            workflow, you can do so at any time
            """
            child = None
        else:
            help_msg = """
            You are ready to explore your attribute association graph! You can choose between a graph-based visually 
            driven exploration, or inspection of your graph data in tabular form. GraphXplore will introduce you to 
            all functionalities and statistical metrics used
            """
            child = ChooseAAGView(self)
        help_col.markdown(help_msg)
        if not self.done:
            self.render_mark_done(parent_obj, child)

class FinishedAAGTabularView(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Finished AAG Tabular View', WorkflowGoal.ExploreAAG, parent)

    def render(self, parent_obj):
        msg = """
        You finished the attribute association graph table view :tada:
        - You can store the results by clicking on "Store results as CSV"
        - You can start new queries by re-clicking "Query database"
        - If you want to proceed with a graph-based data visualization (or any other workflow), you can start a new 
          workflow below
        """
        parent_obj.markdown(msg)
        if not self.done:
            self.render_mark_done(parent_obj, None)

class ReadAAGIntro(Subtask):
    def __init__(self, parent: Optional['Subtask'] = None):
        super().__init__('Read AAG Introduction', WorkflowGoal.ExploreAAG, parent)

    def render(self, parent_obj):
        configured = st.session_state.agg_neo4j_config_check if 'agg_neo4j_config_check' in st.session_state else False
        msg = f"""
        - Click on "Data Exploration" (in the sidebar)-> "Data Exploration" -> "Intro to Attribute Association Graphs"
        - In the tab "Properties" AAGs are explained and all parameters used are explained together with their way of 
          visualization
        - In the tab "Neo4J Quick Start and Configuration" you can learn how to configure and navigate the exploration 
          in Neo4J
            - You need to configure Neo4J before your first exploration {' :heavy_check_mark:' if configured else ''}
        {'- You are ready to explore your dataset :tada:' if configured else ''}
        """
        parent_obj.markdown(msg)
        parent_obj.checkbox('Neo4J is configured according to the guide', key='agg_neo4j_config_check')
        if configured and not self.done:
            self.render_mark_done(parent_obj, None)





