.. _metadatahandling:

graphxplore.MetaDataHandling package
====================================

This subpackage contains functionality based around metadata. You can either define metadata by hand or use the
:class:`~graphxplore.MetaDataHandling.MetaDataGenerator` for automatic extraction from a dataset. The result is a
:class:`~graphxplore.MetaDataHandling.MetaData` object which contains (among others) the following features:

* list of all tables and variables
* primary/foreign key relations between tables
* metadata on the variable-level stored in :class:`~graphxplore.MetaDataHandling.VariableInfo` objects which
  contain:

    * data types (string, integer or decimal) and variable types (primary key, foreign key, metric, or categorical)
    * value distributions
    * detected or annotated artifacts (data type mismatches and extreme outliers)
    * labels and descriptions
    * :class:`~graphxplore.MetaDataHandling.BinningInfo` for assigning metric variable values to bins

The :class:`~graphxplore.MetaDataHandling.MetaData` objects can be stored and loaded as JSON files. The code could
look like this:

::

    >>> from graphxplore.MetaDataHandling import MetaDataGenerator, MetaData
    >>> generator = MetaDataGenerator(csv_data='/dir_with_csv_files')
    >>> metadata = generator.gather_meta_data()
    # the meta data could be adjusted before storage
    >>> metadata.store_in_json(file_path='path/to/json')

Module contents
---------------

.. automodule:: graphxplore.MetaDataHandling
   :members:
   :undoc-members:
   :show-inheritance:
