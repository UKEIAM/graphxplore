.. _metadatahandling:

graphxplore.MetaDataHandling package
====================================

This subpackage contains functionality for automatic extraction self-defining of metadata. Primary keys are detected
for each table and foreign key relations are derived between tables. The generated metadata can be inspected and
adjusted, and finally stored in a JSON file. :class:`~graphxplore.MetaDataHandling.MetaData` is the main storage data
structure. The :class:`~graphxplore.MetaDataHandling.MetaDataGenerator` can be used to automatically extract metadata.
The code could look like this:

::

    >>> from graphxplore.MetaDataHandling import MetaDataGenerator, MetaData
    >>> generator = MetaDataGenerator(source_dir = 'dir_with_csv_files')
    >>> generator.gather_meta_data()
    >>> metadata = generator.result
    # the meta data could be adjusted before storage
    >>> metadata.store_in_json(file_path = 'path_to_json')

:class:`~graphxplore.MetaDataHandling.MetaData` objects contain the primary key of each table and their foreign key
relations within the data set. Additionally, for each variable there exists a
:class:`~graphxplore.MetaDataHandling.VariableInfo` object. This class contains information about the correct data type
of the variable, its origin table and its variable type (primary key, foreign key, metric or categorical). Moreover,
artifacts, distribution of values and data types as well as binning information
(as :class:`~graphxplore.MetaDataHandling.BinningInfo`) for metric variables are inferred. All data should be inspected
and potentially adjusted.

Module contents
---------------

.. automodule:: graphxplore.MetaDataHandling
   :members:
   :undoc-members:
   :show-inheritance:
