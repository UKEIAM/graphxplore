graphxplore.DataMapping.Conditionals package
============================================

Conditional objects check a source line of data (as dictionary) for a specific constraint and return a boolean. E.g. the
:class:`~graphxplore.DataMapping.Conditionals.MetricOperator` checks if the value for a specific variable is of numeric
type and compares it with a given input value. Conditionals can be combined with negations as well as and/or
compositions. All classes of this subpackage have the same interface, inherit from the
:class:`~graphxplore.DataMapping.Conditionals.LogicOperator` class and can be parsed from/to strings. Code might look
like

::

    >>> from graphxplore.MetaDataHandling import DataType
    >>> from graphxplore.DataMapping.Conditionals import MetricOperator, MetricOperatorType, StringOperator, StringOperatorType, AndOperator
    >>> metric_operator = MetricOperator(table='table', variable='var', value=42, data_type=DataType.Integer,
    >>>                                  compare=MetricOperatorType.SmallerOrEqual)
    >>> str(metric_operator)
    '(VARIABLE var OF TYPE Integer IN TABLE table <= 42)'
    >>> source_line = SourceDataLine({'table' : {'var' : 25}})
    >>> metric_operator.valid(source_line)
    True
    >>> source_line = SourceDataLine({'table' : {'var' : 1.5}})
    >>> metric_operator.valid(source_line)
    # 1.5 is not an integer
    False
    >>> string_operator = StringOperator(table='other_table', variable='other_var', value='nana',
    >>>                                  compare=StringOperatorType.Contains)
    >>> and_operator = AndOperator(sub_operators=[metric_operator, string_operator])
    >>> source_line = SourceDataLine({'table' : {'var' : 25}, 'other_table' : {'other_var' : 'apple'}})
    >>> and_operator.valid(source_line)
    # 'nana' not in 'apple'
    False
    >>> source_line = SourceDataLine({'table' : {'var' : 25}, 'other_table' : {'other_var' : 'banana'}})
    >>> and_operator.valid(source_line)
    True

Module contents
---------------

.. automodule:: graphxplore.DataMapping.Conditionals
   :members:
   :undoc-members:
   :show-inheritance:
