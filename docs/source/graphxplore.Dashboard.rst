.. _dashboard:

graphxplore.Dashboard package
====================================

With this subpackage you can generate `plotly <https://plotly.com/python/>`_ distribution plots based on
:class:`~graphxplore.MetaDataHandling.MetaData` or a :class:`~graphxplore.Basis.BaseGraph.BaseGraph` stored in a Neo4J
database. As visualizations, pie and stacked bar charts, as well as histogram, scatter and box plots are used. The
suitable type of visualization is automatically detected based on the type of data to plot. These plots are used in the
GraphXplore application, but you could use them e.g. for a publication or custom dashboard.

The :class:`~graphxplore.Dashboard.MetadataDistributionPlotter` class can be used to plot data type and value
distributions contained in a :class:`~graphxplore.MetaDataHandling.MetaData` object. Data type distributions are
plotted as pie charts, value distributions as box plots for metric variables and as pie charts for categorical
variables. Note that the plotted data is already represented in the :class:`~graphxplore.MetaDataHandling.MetaData` and
does not need to be queried from the dataset.

The :class:`~graphxplore.Dashboard.DashboardBuilder` class retrieves univariate (one variable) and bivariate (two
variables that are analyzed together) distributions from a Neo4J database and plots them. Here, the combined strength
of the detailed :class:`~graphxplore.MetaDataHandling.MetaData` objects and efficient (potentially multi-table) joins
in Neo4J Cypher are leverage to create plots on the fly. Additionally, you can define subgroups within your dataset
using the :class:`~graphxplore.GraphDataScience.GroupSelector` class to combine and compare distributions in different
groups in one plot. Based on the distribution and data type the following plots are generated:

- Univariate distributions:

  - Categorical variables: One or multiple pie charts (one per group)
  - Metric variables: One or multiple overlaid histograms (one per group)

- Bivariate distributions:

  - Two categorical variables: One or multiple stacked bar charts (one per group)
  - One categorical and one metric variable: One or multiple subplots (one per group) each with multiple box plots
    (one per category)
  - Two metric variables: One ore multiple overlaid scatter plots (one per group)

Code might look like

::

    >>> from graphxplore.Dashboard import DashboardBuilder, MetadataDistributionPlotter, HistogramYScaleType
    >>> from graphxplore.MetaDataHandling import MetaData
    >>> from graphxplore.GraphDataScience import GroupSelector
    >>> from graphxplore.DataMapping.Conditionals import StringOperator, StringOperatorType
    >>>
    >>> meta = MetaData.load_from_json(filepath='/path/meta.json')
    >>> metric = meta.get_variable(table='table', variable='metric_variable')
    >>> categorical = meta.get_variable(table='other_table', variable='categorical_variable')
    # data type distributions are always plotted with pie charts
    >>> data_type_plot = MetadataDistributionPlotter.plot_data_type_distribution(metric)
    # plot value distributions
    >>> value_dist_box_plot = MetadataDistributionPlotter.plot_value_distribution(metric)
    >>> value_dist_pie_chart = MetadataDistributionPlotter.plot_value_distribution(categorical)
    # define subgroups for plots
    >>> apple_condition = StringOperator(table='table', variable='food', value='apple', compare=StringOperatorType.Equals)
    >>> pear_condition = StringOperator(table='table', variable='food', value='pear', compare=StringOperatorType.Equals)
    >>> subgroups = {'apples' : GroupSelector(group_table='table', meta=meta, group_filter=apple_condition),
    >>>              'pears' : GroupSelector(group_table='table', meta=meta, group_filter=pear_condition)}
    # define the builder, add the subgroups and exclude the full table 'table' as a group
    >>> builder = DashboardBuilder(meta=meta, main_table='table', base_graph_database='mydb', full_table_group=False,
    >>>                            groups=subgroups, address='bolt://localhost:7687', auth=('my_user', 'my_password'))
    # query metric variable and plot two overlaid histograms. Use fraction (instead of count) for y-scale
    >>> hist_plot = builder.get_variable_dist_plot(table='table', variable='metric_variable',
    >>>                                            y_scale_type=HistogramYScaleType.Fraction)
    # query categorical variable and get two pie charts
    >>> pie_plot = builder.get_variable_dist_plot(table='other_table', variable='categorical_variable')
    # query both variables and plot as two subplots (per group) with box plots (one per category of 'categorical_variable')
    # notice how the two variables can originate from different tables (must both be reachable via foreign table relations from 'table')
    >>> bivariate_box_plot = builder.get_correlation_plot(first_table='table', first_var='metric_variable',
    >>>                                                   second_table='other_table', second_var='categorical_variable')


Module contents
---------------

.. automodule:: graphxplore.Dashboard
   :members:
   :undoc-members:
   :show-inheritance:
