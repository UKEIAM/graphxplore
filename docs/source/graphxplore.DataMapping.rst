.. _datamapping:

graphxplore.DataMapping package
===============================

This subpackage can be used to clean your data from artifacts or conduct ETL processes. The workflows of this package
are independent of the :ref:`graphtranslation` and :ref:`graphdatascience` and can in principal be used without the
necessity of graph-based data representation. All ETL processes can be stored as JSON file for reusability.

The central class is :class:`~graphxplore.DataMapping.DataMapping`. It contains the
:class:`~graphxplore.MetaDataHandling.MetaData` objects of the source dataset and the target data structure.
For each variable (with the exception of some primary keys) of the target structure a
:class:`~graphxplore.DataMapping.VariableMapping` must be defined. A
:class:`~graphxplore.DataMapping.VariableMapping` contains one or multiple
:class:`~graphxplore.DataMapping.MappingCase` objects which in turn each contain a
:class:`~graphxplore.DataMapping.Conditionals.LogicOperator` and a
:class:`~graphxplore.DataMapping.Conclusions.Conclusion`. The :class:`~graphxplore.DataMapping.MappingCase` objects are
checked in input order. If the :class:`~graphxplore.DataMapping.Conditionals.LogicOperator` returns ``True`` on the
given source line the return of the :class:`~graphxplore.DataMapping.Conclusions.Conclusion` is triggered. If the
:class:`~graphxplore.DataMapping.Conditionals.LogicOperator` returns ``False`` the next
:class:`~graphxplore.DataMapping.MappingCase` is checked. If no conditional is met, ``None`` is returned. Code for a
single :class:`~graphxplore.DataMapping.VariableMapping` could look like

::

    >>> from graphxplore.MetaDataHandling import DataType
    >>> from graphxplore.DataMapping import VariableMapping, MappingCase
    >>> from graphxplore.DataMapping.Conditionals import StringOperator, StringOperatorType, MetricOperator, MetricOperatorType, AndOperator, AlwaysTrueOperator
    >>> from graphxplore.DataMapping.Conclusions import CopyConclusion, FixedReturnConclusion
    # value for variable 'var' is decimal, larger than 0 and value for variable 'another_val' is a string and contains 'nana'
    # then copy value for variable 'var'
    >>> first_case = MappingCase(conditional=AndOperator(sub_operators=[
    >>>         MetricOperator(table='FirstSourceTable', variable='var', value=0, data_type=DataType.Decimal,
    >>>                        compare=MetricOperatorType.Larger),
    >>>         StringOperator(table='SecondSourceTable', variable='another_var', value='nana',
    >>>                        compare=StringOperatorType.Contains)
    >>>                 ]), conclusion=CopyConclusion(target_data_type=DataType.Decimal,
    >>>                                               origin_table='FirstSourceTable', var_to_copy='var'))
    # always return 0.0
    >>> second_case = MappingCase(conditional=AlwaysTrueOperator(), conclusion=FixedReturnConclusion(DataType.Decimal,
    >>>                           return_val=0.0))
    >>> var_mapping = VariableMapping(target_table='TargetTable', target_variable='target_var',
    >>>                               cases=[first_case, second_case])
    >>> source_line = SourceDataLine({'FirstSourceTable' : {'var' : 1.5}, 'SecondSourceTable' : {'another_var' : 'banana'}})
    >>> var_mapping[source_line]
    # first case is met
    1.5
    >>> source_line = SourceDataLine({'FirstSourceTable' : {'var' : -7.8}, 'SecondSourceTable' : {'another_var' : 'banana'}})
    >>> var_mapping[source_line]
    # first case not met because 'var' is negative -> second case is executed
    0.0
    >>> source_line = SourceDataLine({'FirstSourceTable' : {'var' : 1.5}, 'SecondSourceTable' : {'another_var' : None}})
    >>> var_mapping[source_line]
    # first case not met because 'another_var' has a missing value -> second case is executed
    0.0

You can see from this code snippet that data from different source tables can be combined. This is achieved by
gathering all source data that is associated with one primary key `pk` in table `t` with value `x` into a single
:class:`~graphxplore.DataMapping.SourceDataLine` using the foreign key relations within the source dataset which are
captured in a :class:`~graphxplore.DataMapping.MetaLattice` objects. Data from
other tables that appear as foreign tables in `t` (or related across multiple tables) can be seen as a property of `pk`
and directly added to the :class:`~graphxplore.DataMapping.SourceDataLine` for `x`. Data from tables that reference
themselves `pk` as a foreign key can be aggregated with
:class:`~graphxplore.DataMapping.Conditionals.AggregatorOperator` or
:class:`~graphxplore.DataMapping.Conclusions.AggregateConclusion` objects. Here, all data from lines where `x` is a
foreign key value for `pk` (or across multiple tables) is gathered and some aggregate calculated (e.g. count,
minimal value, etc.). This can be useful e.g. for aggregation of time series.

Because of this strategy, it is important to identify most primary keys of the target data structure with primary keys
of the source dataset. An exception are primary keys of the target data structure that are also referenced as foreign
keys. These can be generated automatically (will be 0-indexed integers) and do not have to have an analog in the
source dataset. :class:`~graphxplore.DataMapping.VariableMapping` of primary keys with one (or multiple) analog can
look like this

::

    >>> from graphxplore.MetaDataHandling import DataType
    >>> from graphxplore.DataMapping import VariableMapping, MappingCase
    >>> from graphxplore.DataMapping.Conditionals import MetricOperator, MetricOperatorType, AlwaysTrueOperator
    >>> from graphxplore.DataMapping.Conclusions import CopyConclusion, MergePrimaryKeysConclusion, ConcatenateTablesConclusion
    # copy primary key 'source_pk' of 'SourceTable' to primary key 'target_pk' of 'TargetTable' (one-to-one mapping)
    >>> one_to_one = VariableMapping(target_table='TargetTable', target_variable='target_pk', cases=[
    >>>         MappingCase(conditional=AlwaysTrueOperator(),
    >>>                     conclusion=CopyConclusion(origin_table='SourceTable', target_data_type=DataType.Integer,
    >>>                                               var_to_copy='source_pk'))])
    # copy primary key 'source_pk' of 'SourceTable' to primary key 'target_pk' of 'TargetTable'
    # only if value for variable 'var' is an integer and equals 0 (filtered one-to-one mapping)
    >>> filtered_one_to_one = VariableMapping(target_table='TargetTable', target_variable='target_pk', cases=[
    >>>         MappingCase(conditional=MetricOperator(table='OtherSourceTable', variable='var', value=0,
    >>>                     data_type=DataType.Integer, compare=MetricOperatorType.Equals),
    >>>                     conclusion=CopyConclusion(origin_table='SourceTable', target_data_type=DataType.Integer,
    >>>                                               var_to_copy='source_pk'))])
    # merge the primary keys (and data) of two source tables 'FirstSourceTable' and 'SecondSourceTable' into a single
    # target primary key 'target_pk'. SourceDataLine objects from 'FirstSourceTable' and 'SecondSourceTable' with the
    # same value for 'source_pk' are merged. This can be used
    >>> merge = VariableMapping(target_table='TargetTable', target_variable='target_pk', cases=[
    >>>         MappingCase(conditional=AlwaysTrueOperator(),
    >>>                     conclusion=MergePrimaryKeysConclusion(tables_keys_to_merge={
    >>>                         'FirstSourceTable' : 'source_pk',
    >>>                         'SecondSourceTable' : 'source_pk'
    >>>                                                           }, target_data_type=DataType.Integer)])
    # data from two source tables 'FirstSourceTable' and 'SecondSourceTable' is processed one after another into
    # SourceDataLine objects and  concatenated into a single target table 'TargetTable'
    >>> concat = VariableMapping(target_table='TargetTable', target_variable='target_pk', cases=[
    >>>         MappingCase(conditional=AlwaysTrueOperator(),
    >>>                     conclusion=ConcatenateTablesConclusion(tables_to_append=['FirstSourceTable',
    >>>                                                            'SecondSourceTable'])])

Data mapping can be quite complex and there exist many functionalities in this subpackage.
:class:`~graphxplore.DataMapping.DataMappingUtils` can be used to ease some common workflows. For further impressions
check out `test/DataMapping/test_data_mapping.py` in the graphxplore git repository.

Submodules
-----------

.. toctree::
   :maxdepth: 1

   graphxplore.DataMapping.Conclusions
   graphxplore.DataMapping.Conditionals

Module contents
---------------

.. automodule:: graphxplore.DataMapping
   :members:
   :undoc-members:
   :show-inheritance:
