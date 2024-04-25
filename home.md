---
title: Welcome to GraphXplore!
author: Louis Bellmann
permalink: /
nav_order: 1
---

<img src="./graphxplore_icon.png" alt="drawing" width="100"/>

# Welcome to GraphXplore!

## About

GraphXplore is a tool for visually exploring, cleaning and transforming your data, as well as defining and sharing 
metadata and mappings with others. It can be used without prior coding/scripting skills and does not require 
advanced knowledge about statistics or data science. The tool was designed with the application to the medical 
research domain in mind, but can be generally used with any data source. An overview of GraphXplore functionalities can 
be found [here]({{ site.baseurl }}{% link functionalities.md %}).

## Installation

The tool can be used as a standalone desktop tool with graphical user interface, local webserver, or as a Python package:
 - Desktop tool: Releases can be accessed [here](https://github.com/UKEIAM/graphxplore/releases)
 - Local webserver: Clone the [GraphXplore repository](https://github.com/UKEIAM/graphxplore), install streamlit with `pip install streamlit`, navigate to 
  `frontend/GraphXplore` and run `streamlit run streamlit_app.py`
 - Python package: Install from PyPi with `pip install graphxplore`, or checkout 
   [available versions](https://pypi.org/project/graphxplore/). Take a look at the [package documentation](https://graphxplore.readthedocs.io/en/latest/)

For data exploration, GraphXplore uses [Neo4J database management system](https://neo4j.com/) for storage and 
graph-based visualization. A guide how to install it can be found 
[here]({{ site.baseurl }}{% link neo4j_installation.md %}#installation).