import streamlit as st
from src.utils import ICON_PATH, get_how_to_image_path
from src.workflow_widgets import Workflow


if __name__ == '__main__':

    st.set_page_config(page_title='Home', page_icon= ICON_PATH)

    workflow = Workflow()
    workflow.render()

    title_col, mid, image_col = st.columns([18,1,1])
    title_col.title('Welcome to GraphXplore!')
    image_col.image(ICON_PATH, width=60)

    st.header('About')
    """
    GraphXplore is a tool for visually exploring, cleaning and transforming your data, as well as defining and sharing 
    meta data and mappings with others. It can be used without prior coding/scripting skills and does not require 
    advanced knowledge about statistics or data science. The tool was designed with the application to the medical 
    research domain in mind, but can be generally used with any data source. You can navigate to the specific task 
    pages using the sidebar to the left. If you prefer GraphXplore as a Python package, you can install it with 
    `pip install graphxplore`
    """

    st.header('Overview')

    """
    GraphXplore can be used for different tasks related to your data. These tasks can be tackled independently, or in 
    conjunction. If you are new to GraphXplore and want to work with your data, you can define your own workflow in the 
    sidebar to the left by picking your desired goal and the tool will guide you through the workflow. Additionally, 
    you can read about the three broad application categories of GraphXplore as well as a Neo4J installation guide 
    below in more detail.
    """

    meta_tab, trans_tab, explore_tab, install_tab = st.tabs([
        'Metadata', 'Data Transformation', 'Data Exploration', 'Neo4J Installation'])

    with meta_tab:
        """
        When working with data it can be useful to get a sense of the character of your dataset at hand. How many 
        tables are in my dataset? How are the tables related to each other? What kind of variables are in my dataset? 
        How is the data distributed? What about missing data? Answering these questions is technically data about data, 
        hence the name *metadata*.  
        Metadata is at the core of all GraphXplore functionalities, it enables the tool to execute complex queries and 
        data augmentations without bothering you with the details. You can automatically extract metadata from your 
        dataset, create it from scratch, and store/load it as a JSON file. Note that the metadata itself does not 
        contain the potential sensitive original data (e.g. patient related data) which can be interesting for sharing 
        insights with other researchers. GraphXplore metadata contains (among others) the following features:
        - list of all tables and variables
        - primary/foreign key relations between tables
        - data types (string, integer or decimal) and variable types (metric or categorical)
        - value distributions
        - detected or annotated artifacts (data type mismatches and extreme outliers)
        - labels and descriptions
        """

    with trans_tab:
        """
        Frequently, you might find that your dataset is not yet in the format that is suitable to start your 
        analysis or other data task. Does your dataset contain artifacts or missing values that need to be handled? Do 
        you need to join tables or split them? Do you need to define new variables based on existing data? This kind of 
        preprocessing is called *data transformation* in GraphXplore.  
        Simple transformation tasks such as cleaning artifacts from your dataset can be achieved in GraphXplore with a 
        few button clicks. For more complex transformations you will need to define a *data mapping*. A data mapping 
        contains human-readable logical expressions to define how tables and variables will be transformed.  
        Similar to the relationship between actual data and metadata, a data mapping describes how a data 
        transformation would be done without actually creating the transformed dataset. As a result, the data mapping 
        itself can be shared and reviewed without access to the actual data. GraphXplore uses metadata to assist during 
        mapping definition and to ensure the validity.
        """

    with explore_tab:
        """
        Most likely you use GraphXplore because you want to analyze your dataset. When your dataset is in a suitable 
        state and you extracted metadata, you are now ready for the data analysis! All analysis in GraphXplore is fully 
        exploratory (this is called *data exploration*) and that has two implications: Firstly, you don't need any 
        hypothesis or prior knowledge of your dataset, you will get to know it during the analysis. Secondly, you will 
        not be able to do statistical inference with GraphXplore as you might be accustomed to in null-hypothesis 
        significance testing. A thorough statistical inference should follow the data exploration, once you explored 
        your dataset and formulated a hypothesis.  
        The data exploration in GraphXplore relies heavily on *visualization* and robust, simple statistical metrics. 
        This way, you don't need advanced statistical knowledge to interpret the results and assess their 
        applicability. Initially, your dataset is stored in a Neo4J graph database for efficient retrieval during the 
        data exploration. Afterwards, you have two ways of exploring your dataset which you can use independently or in 
        conjunction:
        - A classic *dashboard* approach where variable distributions and joint distributions of variable pairs are 
          visualized as pie or bar charts, and scatter or box plots.
        - A novel statistical analysis representation called *attribute association graph*. This graph captures several 
          statistical parameters of single variable values and their conditional dependencies, and visualizes them 
          using colors, shapes and arrows. Alternatively, the statistical parameters can be retrieved in tabular form.
          
        For both approaches, you can define subgroups in your dataset (e.g. disease and control group) and the 
        analysis will resolve to the group-level where you can compare results between groups.
        """

    with install_tab:
        msg_1 = """
        GraphXplore is based on the Neo4J graph-based data platform. Here, you can read information on how 
        to install the Neo4J Desktop tool and configure it for the usage with GraphXplore. If you want to use Neo4J 
        with Docker, checkout [https://neo4j.com/developer/docker-run-neo4j/](https://neo4j.com/developer/docker-run-neo4j/).
        For installation of Neo4J Desktop, follow these steps:
        - Download and install Neo4J Desktop from [https://neo4j.com/download/](https://neo4j.com/download/) and start 
          the application
        - In Neo4J Desktop, click on Projects in the upper left corner and add a new project. Optionally, you can 
          rename the project
        """
        st.markdown(msg_1)
        st.image(get_how_to_image_path('neo4j_install_1'))
        msg_2 = """
        - Next, how have to add a new database management system (DBMS) to your Project:
            - Click on your project in the left corner
            - then on "Add"
            - Add a local DBMS
        """
        st.markdown(msg_2)
        st.image(get_how_to_image_path('neo4j_install_2'))
        msg_3 = """
        - GraphXplore requires the APOC plugin for Neo4J. To install it:
            - Click on your newly created DBMS
            - then on "Plugins" to the right
            - Click on "APOC" and then on "Install"
        """
        st.markdown(msg_3)
        st.image(get_how_to_image_path('neo4j_install_3'))



    # show_pages(
    #     [
    #         Page("streamlit_app.py", "Home", "🏠"),
    #         Page("pages/1_Metadata.py", "Metadata"),
    #         Page("pages/2_Data_Transformation.py", "Data Mapping"),
    #         Page("pages/3_Data_Exploration.py", "Data Exploration"),
    #     ]
    # )