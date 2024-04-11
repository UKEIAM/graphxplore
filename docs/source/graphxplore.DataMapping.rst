.. _datamapping:

graphxplore.DataMapping package
===============================

This subpackage can be used to clean your data from artifacts or conduct more complex ETL processes. The workflows of
this package are independent of the :ref:`graphtranslation` and :ref:`graphdatascience` and can be used without the
necessity for graph-based data representation. All ETL processes can be stored as JSON files for reusability.

The central class is :class:`~graphxplore.DataMapping.DataMapping`. It contains the
:class:`~graphxplore.MetaDataHandling.MetaData` objects of the source dataset and the target data structure.
It contains mappings between the source and target tables as :class:`~graphxplore.DataMapping.TableMapping` objects.
These can describe one-to-one, one-to-many, many-to-one, or many-to-many relationships.
Mapping rules on the variable-level are stored as :class:`~graphxplore.DataMapping.VariableMapping` objects. They must
be defined for each variable (with the exception of primary keys and some foreign keys) of the target data structure.
Each :class:`~graphxplore.DataMapping.VariableMapping` contains one or multiple
:class:`~graphxplore.DataMapping.MappingCase` objects which in turn each contain a
:class:`~graphxplore.DataMapping.Conditionals.LogicOperator` and a
:class:`~graphxplore.DataMapping.Conclusions.Conclusion`. The :class:`~graphxplore.DataMapping.MappingCase` objects are
checked in input order. If the function :func:`~graphxplore.DataMapping.Conditionals.LogicOperator.valid` of the
:class:`~graphxplore.DataMapping.Conditionals.LogicOperator` returns ``True`` on the
given unit of source data, :func:`~graphxplore.DataMapping.Conclusions.Conclusion.get_return` of the
:class:`~graphxplore.DataMapping.Conclusions.Conclusion` is triggered. If
:class:`~graphxplore.DataMapping.Conditionals.LogicOperator.valid` returns ``False`` the next
:class:`~graphxplore.DataMapping.MappingCase` is checked. If no conditional is met, ``None`` is returned. Code for a
single :class:`~graphxplore.DataMapping.VariableMapping` could look like

::

    >>> from graphxplore.MetaDataHandling import DataType
    >>> from graphxplore.DataMapping import VariableMapping, MappingCase, SourceDataLine
    >>> from graphxplore.DataMapping.Conditionals import (StringOperator, StringOperatorType, MetricOperator,
    >>>                                                   MetricOperatorType, AndOperator, AlwaysTrueOperator)
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

This automation strategy is enabled by the :class:`~graphxplore.DataMapping.TableMapping` which must be defined for
each target table. Examples might look like:

::

    >>> from graphxplore.MetaDataHandling import MetaData, DataType
    >>> from graphxplore.DataMapping import TableMapping, MappingCase, TableMappingType, DataMapping
    >>> from graphxplore.DataMapping.Conditionals import MetricOperator, MetricOperatorType, AlwaysTrueOperator
    >>>
    >>> source_meta = MetaData.load_from_json(filepath='/source_meta.json')
    >>> target_meta = MetaData.load_from_json(filepath='/target_meta.json')
    >>> data_mapping = DataMapping(source=source_meta, target=target_meta)
    # one-to-one mapping between 'SourceTable' and 'TargetTable'
    # each source data line will contain a row of 'SourceTable' and one row of each foreign table (potentially across
    # foreign table chains) of the corresponding foreign key value
    >>> one_to_one = TableMapping(type=TableMappingType.OneToOne, source_tables=['SourceTable'])
    >>> data_mapping.assign_table_mapping(table='TargetTable', table_mapping=one_to_one)
    # again a one-to-one mapping, but with an added condition. If this condition is not met for a source data line, the
    # whole line will be skipped. Adding condition is possible for all table mapping types except inherited table mappings
    >>> added_condition = MetricOperator(table='ForeignSourceTable', variable='var', value=0,
    >>>                                  data_type=DataType.Integer, compare=MetricOperatorType.Equals)
    >>> filtered_one_to_one = TableMapping(type=TableMappingType.OneToOne, source_tables=['SourceTable'],
    >>>                                    condition=added_condition)
    >>> data_mapping.assign_table_mapping(table='TargetTable', table_mapping=filtered_one_to_one)
    # merge the the of two source tables 'FirstSourceTable' and 'SecondSourceTable' into a single
    # target table 'TargetTable' (many-to-one). SourceDataLine objects from 'FirstSourceTable' and 'SecondSourceTable'
    # with the same primary key value are merged. This way, data rows from multiple source tables can be combined into
    # one target data row
    >>> merge = TableMapping(TableMappingType.Merge, source_tables=['FirstSourceTable', 'SecondSourceTable'])
    >>> data_mapping.assign_table_mapping(table='TargetTable', table_mapping=merge)
    # data from two source tables 'FirstSourceTable' and 'SecondSourceTable' is processed one after another into
    # SourceDataLine objects and concatenated into a single target table 'TargetTable' (many-to-one). No merging of
    # source data rows is conducted
    >>> concatenate = TableMapping(TableMappingType.Concatenate, source_tables=['FirstSourceTable', 'SecondSourceTable'])
    >>> data_mapping.assign_table_mapping(table='TargetTable', table_mapping=concatenate)
    # If 'ForeignTargetTable' is a foreign table (or foreign table of foreign table ...) of 'TargetTable', it can
    # inherit the mapping type of 'TargetTable'. the rows of both tables will be created together and thus the
    # result data will be split. This can be useful to make the target dataset for manageable. If the relation of
    # 'TargetTable' is 'one-to-one', this will become 'one-to-many'. If  its relation is 'many-to-one', it will become
    # 'many-to-many'.
    >>> inherited = TableMapping(TableMappingType.Inherited, to_inherit='TargetTable')
    >>> data_mapping.assign_table_mapping(table='ForeignTargetTable', table_mapping=inherited)

Data mapping can be quite complex and there exist many functionalities in this subpackage.
:class:`~graphxplore.DataMapping.DataMappingUtils` can be used to ease some common workflows. For further impressions
check out `test/DataMapping/test_data_mapping.py` in the
`graphxplore Github repository <https://github.com/UKEIAM/graphxplore>`_.

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
