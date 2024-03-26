graphxplore.DataMapping.Conclusions package
===========================================

Conclusions objects take a source line of data (as dictionary) and return a specific value based on the input. E.g. the
:class:`~graphxplore.DataMapping.Conclusions.CopyConclusion` just copies/returns a specific input value. All classes of
this subpackage have the same interface, inherit from the :class:`~graphxplore.DataMapping.Conclusions.Conclusion`
class and can be parsed from/to strings. Code might look like

::

    >>> from graphxplore.MetaDataHandling import DataType
    >>> from graphxplore.DataMapping import SourceDataLine
    >>> from graphxplore.DataMapping.Conclusions import CopyConclusion
    >>> conclusion = CopyConclusion(target_data_type=DataType.Integer, origin_table='table', var_to_copy='var')
    >>> print(str(conclusion))
    'COPY VARIABLE var IN TABLE table IF TYPE IS Integer'
    >>> source_line = SourceDataLine({'table' : {'var' : 42}})
    >>> conclusion.get_return(source_line)
    42
    >>> source_line = SourceDataLine({'table' : {'var' : 'some_value'}})
    >>> conclusion.get_return(source_line)
    # 'some_value' is not an integer and thus will not get copied
    None

Module contents
---------------

.. automodule:: graphxplore.DataMapping.Conclusions
   :members:
   :undoc-members:
   :show-inheritance:
