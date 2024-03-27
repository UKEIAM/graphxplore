.. GraphXplore documentation master file, created by
   sphinx-quickstart on Wed Mar 15 14:27:08 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to GraphXplore's documentation!
=======================================

This package gives functionality for ETL processes exploratory data analysis of large data sources using graphs.
The starting point is always a directory of relational table data contained in CSV files. A typical workflow could look
like this:

#. Extract, inspect and potentially adjust metadata information with :ref:`metadatahandling`

#. Clean artifacts and transform data with :ref:`datamapping`

#. Convert the relational data into a graph structure (and load into a Neo4J database) with :ref:`graphtranslation`

#. Generate dashboards and graph-based visualizations for easy exploratory data analysis with :ref:`graphdatascience`

Subpackages
-----------

.. toctree::
   :maxdepth: 1

   graphxplore.Basis
   graphxplore.MetaDataHandling
   graphxplore.DataMapping
   graphxplore.GraphTranslation
   graphxplore.GraphDataScience

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
