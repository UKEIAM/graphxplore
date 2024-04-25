---
title: Functionalities Overview
permalink: /functionalities
nav_order: 2
---

# GraphXplore Functionalities Overview
{: .no_toc }

GraphXplore can be used for different tasks related to your data. These tasks can be tackled independently, or in 
conjunction. If you are new to data-driven analysis, you can read about the three broad application categories of 
GraphXplore below in more detail.

## Table of contents
{: .no_toc .text-delta } 
- TOC
{:toc}

## Metadata

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
  - detected or annotated artifacts (data type mismatches, typos and extreme outliers)
  - labels and descriptions

## Data Transformation

Frequently, you might find that your dataset is not yet in the format that is suitable to start your 
analysis or other data task. Does your dataset contain artifacts or missing values that need to be handled? Do 
you need to join tables or split them? Do you need to define new variables based on existing data? This kind of 
preprocessing is called *data transformation* in GraphXplore.  
Simple transformation tasks such as cleaning artifacts from your dataset, adding primary keys or table pivotization can 
be achieved in GraphXplore with a few button clicks or Python function calls.

For more complex transformations you will need to define a *data mapping*.
A data mapping contains human-readable logical expressions to define how tables and variables will be transformed.  
Similar to the relationship between actual data and metadata, a data mapping describes how a data 
transformation would be done without actually creating the transformed dataset. As a result, the data mapping 
itself can be shared and reviewed without access to the actual data. GraphXplore uses metadata to assist during 
mapping definition and to ensure the mapping's validity.

## Data Exploration

Most likely you use GraphXplore because you want to analyze your dataset. When your dataset is in a suitable 
state and you extracted metadata, you are now ready for the data analysis! All analysis in GraphXplore is fully 
exploratory (this is called *data exploration*) and that has two implications: Firstly, you don't need any 
hypothesis or prior knowledge of your dataset, you will get to know it during the analysis. Secondly, you will 
not be able to do statistical inference with GraphXplore as you might be accustomed to in null-hypothesis 
significance testing. A thorough statistical inference should follow the data exploration, once you explored 
your dataset and formulated a hypothesis.

The data exploration in GraphXplore relies heavily on visualization and robust, simple statistical metrics. 
This way, you don't need advanced statistical knowledge to interpret the results and assess their 
applicability. Initially, your dataset is stored in a [Neo4J graph database](https://neo4j.com/) 
(read [here]({{ site.baseurl }}{% link neo4j_installation.md %}) for the installation) for efficient retrieval during the data 
exploration. Afterwards, you have two ways of exploring your dataset which you can use independently or in conjunction:

- A classic *dashboard* approach where variable distributions and joint distributions of variable pairs are 
  visualized as pie or bar charts, and scatter or box plots.
- A novel statistical analysis representation called 
- [attribute association graph]({{ site.baseurl }}{% link aag_intro.md %}). This graph captures several 
  statistical parameters of single variable values and their conditional dependencies, and visualizes them 
  using colors, shapes and arrows. Alternatively, the statistical parameters can be retrieved in tabular form.
  
For both approaches, you can define subgroups in your dataset (e.g. disease and control group) and the 
analysis will resolve to the group-level where you can compare results between groups.
