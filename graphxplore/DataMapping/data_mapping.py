import os
import json
import copy
from dataclasses import dataclass, field, asdict
from typing import Union, Mapping, Dict, List, Optional, Tuple
from graphxplore.MetaDataHandling import MetaData, VariableType
from graphxplore.Basis import BaseUtils
from .Conditionals import LogicOperator, LogicOperatorParser, AlwaysTrueOperator
from .Conclusions import Conclusion
from .meta_lattice import MetaLattice
from .variable_mapping import VariableMapping
from .data_structure_transformer import TableMappingType

@dataclass
class TableMapping:
    """
    Each target table x must have some relationship to one or multiple source tables.
    Using this relationship, single units of source data are formed. Variable mappings are applied to these
    units to form a single output row of *x*. Variables of the related source tables and their foreign
    tables (and their foreign tables, and so on...) will have a single value (might be a missing value) in
    this unit of source data. These variables are called singular variables. Variables of inverted
    foreign tables (*a* is an inverted foreign table of *b*, if *b* is a foreign table of *a*), might have
    multiple values in a unit of source data (e.g. timeseries, or multiple blood measurements for a single
    patient). They are called aggregate variables. For a table mapping you have the following options:

    - *x* has a one-to-one relationship with a single source table *y*. Primary key values are copied
      from *y* to *x*. A unit of source data is formed by a single row of *y* and rows from
      foreign tables and/or inverted foreign tables of *y*. (Most common option)
    - *x* has a one-to-many relationship with multiple source tables. The data of the source tables (and
      foreign tables or inverted foreign tables) will be combined to form a single unit of source data.
      This can be done in two ways:

        - The data of the source tables can be merged. Here, data rows from different source tables are
          combined to a single unit, if the row's primary key values are identical. If a primary key value
          of a source table has no analog in another source table, its row is taken independently.
        - The data of the source tables can be concatenated. Here, the source tables are processed
          independently one after the other to form units of source data together with their foreign tables or
          inverted foreign tables. The primary key values of *x* will be 0-indexed integers.

    - If *x* is a foreign table of another target table *x'*, the relationship to source tables can be
      inherited from *x'*. If *x'* itself inherits the relationship of another target table *x''*, this
      inheritance is propagated to *x*. The primary key values of *x* will be 0-indexed integers and all its rows
      will be de-duplicated. The primary key values of *x* will be used as foreign key values in *x'*.

    Optionally, you can define a condition to filter out units of source data that should not be considered in
    the mapping. If the condition evaluates to ``False`` for a unit of source data, it is fully removed from the
    transformation process of this target table. By default, the
    :class:`~graphxplore.DataMapping.Conditionals.AlwaysTrueOperator` is used and all source data is taken into the
    transformation
    """
    type : Optional[TableMappingType] = None
    source_tables : List[str] = field(default_factory=list)
    to_inherit : Optional[str] = None
    condition : LogicOperator = AlwaysTrueOperator()

    def to_dict(self) -> Dict[str, Union[str, List[str], None]]:
        result = asdict(self)
        if self.type is not None:
            result['type'] = result['type'].value
        result['condition'] = str(result['condition'])
        return result

    @staticmethod
    def from_dict(input_dict: Dict[str, Union[str, List[str], None]]) -> 'TableMapping':
        if 'type' not in input_dict:
            raise AttributeError('You must specify the type of table mapping at the key "type" in your dict')
        if input_dict['type'] is None:
            mapping_type = None
        else:
            if input_dict['type'] not in TableMappingType._value2member_map_.keys():
                raise AttributeError('Mapping type "' + input_dict['type'] + '" not recognized')
            mapping_type = TableMappingType._value2member_map_[input_dict['type']]
        if 'condition' not in input_dict:
            raise AttributeError('You must specify a condition in your table mapping dict at the key "condition"')
        condition = LogicOperatorParser.from_string(input_dict['condition'])
        if 'source_tables' not in input_dict:
            raise AttributeError('You must specify the source tables of the table mapping at the key "source_tables"')
        if 'to_inherit' not in input_dict:
            raise AttributeError('You must specify the table to inherit from at the key "to_inherit"')
        return TableMapping(type=mapping_type, source_tables=input_dict['source_tables'],
                            to_inherit=input_dict['to_inherit'],condition=condition)

class DataMapping:
    """This class summarizes all individual :class:`VariableMapping` objects for a whole dataset via a dictionary of
    table -> variable -> :class:`VariableMapping`

    :param source: The :class:`~graphxplore.MetaDataHandling.MetaData` of the source dataset
    :param target: The :class:`~graphxplore.MetaDataHandling.MetaData` of the source structure
    :param table_mappings: The table mapping for each table. Can be filled later, defaults to ``None``.
    :param variable_mappings: The dictionary of all variable mappings for all tables. Can be filled later, defaults
        to ``None``.
    """
    def __init__(self, source : MetaData, target : MetaData,
                 table_mappings: Optional[Mapping[str, TableMapping]] = None,
                 variable_mappings : Optional[Mapping[str, Mapping[str, VariableMapping]]] = None):
        """Constructor method
        """
        for table in source.get_table_names():
            if not source.has_primary_key(table):
                raise AttributeError('Source table "' + table + '" has no assigned primary key')
        for table in target.get_table_names():
            if not target.has_primary_key(table):
                raise AttributeError('Target table "' + table + '" has no assigned primary key')
        self.source = source
        self.target = target
        self.source_lattice = MetaLattice.from_meta_data(self.source)
        self.target_lattice = MetaLattice.from_meta_data(self.target)
        if table_mappings is not None:
            for table in self.target.get_table_names():
                if table not in table_mappings:
                    raise AttributeError('Target table "' + table + '" does not exist in table mapping dict')
            self.table_mappings = table_mappings
        else:
            self.table_mappings = {table : TableMapping() for table in self.target.get_table_names()}
        for table, table_mapping in self.table_mappings.items():
            self._check_table_mapping(table, table_mapping)
        if variable_mappings is not None:
            for table in self.target.get_table_names():
                if table not in variable_mappings:
                    raise AttributeError('Target table "' + table + '" does not exist in variable mapping dict')
                pk = self.target.get_primary_key(table)
                if pk in variable_mappings[table]:
                    raise AttributeError('Primary key of target table "' + table
                                         + '" should not exist in variable mapping dict')
                table_mapping_assigned = self.table_mappings[table].type is not None
                singular_source_tables, aggregation_source_tables = None, None
                if table_mapping_assigned:
                    singular_source_tables, aggregation_source_tables = self.get_source_tables_for_var_mappings(table)
                for variable in self.target.get_variable_names(table):
                    if not self.variable_should_get_mapped(table, variable):
                        if variable in variable_mappings[table]:
                            if variable == pk:
                                raise AttributeError('Primary key of target table "' + table
                                                     + '" should not exist in variable mapping dict')
                            else:
                                raise AttributeError(
                                    'Variable "' + variable
                                    + '" is a foreign key that is used for inheritance of table mapping of "'
                                    + table + '". It should not have a variable mapping')
                    else:
                        if variable not in variable_mappings[table]:
                            raise AttributeError('Target variable "' + variable + '" of target table "' + table
                                                 + '" missing in variable mappings')
                        var_mapping = variable_mappings[table][variable]
                        if var_mapping.target_table != table:
                            raise AttributeError('Mismatch in target table "' + table
                                                 + '" in variable mapping dict and "' + var_mapping.target_table
                                                 + '" in variable mapping')
                        if var_mapping.target_variable != variable:
                            raise AttributeError('Mismatch in target variable "' + variable + '" of target table "'
                                                 + table + '" in variable mapping dict and "'
                                                 + var_mapping.target_variable + '" in variable mapping')
                        if not table_mapping_assigned:
                            if len(var_mapping.cases) > 0:
                                raise AttributeError('Target variable "' + variable + '" of table "' + table
                                                     + '" already mapped in variable mapping dict, but its table is '
                                                       'still unmapped')
                        else:
                            self._check_var_mapping(
                                var_mapping, singular_source_tables, aggregation_source_tables)
            self.variable_mappings = variable_mappings
        else:
            self.variable_mappings = {table : {variable : VariableMapping(table, variable, [])
                                      for variable in self.target.get_variable_names(table)
                                      if variable != self.target.get_primary_key(table)}
                                      for table in self.target.get_table_names()}

    def assign_variable_mapping(self, var_mapping : VariableMapping) -> None:
        """Adds a :class:`VariableMapping` object to the collection. If a mapping exists already for the target table
        and variable, it will be overwritten

        :param var_mapping: The variable mapping to add
        """
        self.target.get_variable(var_mapping.target_table, var_mapping.target_variable)
        if self.table_mappings[var_mapping.target_table].type is None:
            raise AttributeError('You have to specify the table mapping for target table "'
                                 + var_mapping.target_table + '" before adding variable mappings')
        if not self.variable_should_get_mapped(var_mapping.target_table, var_mapping.target_variable):
            if var_mapping.target_variable == self.target.get_primary_key(var_mapping.target_table):
                raise AttributeError('"' + var_mapping.target_variable + '" is the primary key of target table "'
                                     + var_mapping.target_table
                                     + '". Primary keys have no own variable mapping. Their mapping behaviour is '
                                       'defined by the table mapping')
            else:
                raise AttributeError('"' + var_mapping.target_variable + '" is a foreign key of target table "'
                                     + var_mapping.target_table
                                     + '" which is used for inheritance of its table mapping. These foreign keys have '
                                       'no own variable mapping. Their mapping behaviour is defined by the table '
                                       'mapping')
        singular_source_tables, aggregation_source_tables = self.get_source_tables_for_var_mappings(var_mapping.target_table)
        self._check_var_mapping(var_mapping, singular_source_tables, aggregation_source_tables)
        if var_mapping.target_table in self.variable_mappings:
            self.variable_mappings[var_mapping.target_table][var_mapping.target_variable] = var_mapping
        else:
            self.variable_mappings[var_mapping.target_table] = {var_mapping.target_variable : var_mapping}

    def get_variable_mapping(self, table : str, variable : str) -> VariableMapping:
        """Retrieves the :class:`VariableMapping` for the given table and variable. Raises an exception if the table
        or variable does not exist in the collection

        :param table: The target table of the variable to map
        :param variable: The name of the variable
        :return: Returns the retrieved variable mapping
        """
        if table not in self.variable_mappings:
            raise AttributeError('Table "' + table + '" does not exist in data mapping')
        if not self.variable_should_get_mapped(table, variable):
            if variable == self.target.get_primary_key(table):
                raise AttributeError('"' + variable + '" is the primary key of target table "' + table
                                     + '". Primary keys have no own variable mapping. Their mapping behaviour is defined by '
                                       'the table mapping')
            else:
                raise AttributeError('"' + variable + '" is a foreign key of target table "' + table
                                     + '" which is used for inheritance of its table mapping. These foreign keys have '
                                       'no own variable mapping. Their mapping behaviour is defined by the table '
                                       'mapping')
        if variable not in self.variable_mappings[table]:
            raise AttributeError('Variable "' + variable + ' does not exist in data mapping for table "' + table + '"')
        return self.variable_mappings[table][variable]

    def assign_table_mapping(self, table: str, table_mapping: TableMapping):
        """Assign the table mapping for ``table``. This overwrites any existing table mapping

        :param table: The table the mapping gets assigned to
        :param table_mapping: The table mapping that gets assigned
        """
        self._check_table_mapping(table, table_mapping)
        old_mapping = copy.deepcopy(self.table_mappings[table])
        self.table_mappings[table] = table_mapping
        # remove variable mapping of foreign key in inherited table, if it was defined before
        if table_mapping.type == TableMappingType.Inherited:
            foreign_key = self.target.get_primary_key(table)
            if foreign_key in self.variable_mappings[table_mapping.to_inherit]:
                del self.variable_mappings[table_mapping.to_inherit][foreign_key]
        # add empty variable mapping for foreign key
        elif old_mapping.type is not None and old_mapping.type == TableMappingType.Inherited:
            foreign_key = self.target.get_primary_key(table)
            foreign_table = old_mapping.to_inherit
            self.variable_mappings[foreign_table][foreign_key] = VariableMapping(foreign_table, foreign_key, [])


    def get_table_mapping(self, table: str) -> TableMapping:
        """Returns the table mapping for ``table`` if it exists

        :param table: The table to retrieve the mapping for
        :return: Returns the retrieved mapping or raises an exception if it does not exist
        """
        if table not in self.table_mappings:
            raise AttributeError('Table "' + table + '" does not exist in data mapping')
        return self.table_mappings[table]

    def foreign_key_is_for_inheritance(self, table: str, foreign_key: str) -> bool:
        """Checks if ``foreign_key`` is marked for inheritance, i.e its foreign table inherits the table mapping
        from ``table``

        :param table: The target table to check the foreign key for
        :param foreign_key: The foreign key, an exception will be raised if this is not a foreign key of table ``table``
        :return: Returns ``True`` if the foreign table of ``foreign_key`` is inheriting from ``table``
        """
        if foreign_key not in self.target.get_foreign_keys(table):
            raise AttributeError('"' + foreign_key + '" is not a foreign key of target table "' + table + '"')
        foreign_table = self.target.get_foreign_keys(table)[foreign_key]
        foreign_table_mapping = self.table_mappings[foreign_table]
        return foreign_table_mapping.type == TableMappingType.Inherited and foreign_table_mapping.to_inherit == table

    def to_dict(self) -> Dict[str, Dict[str, Dict[str, Union[str, List[Dict[str, str]]]]]]:
        """Converts the object to a dictionary containing only strings

        :return: Returns a dictionary containing all mappings
        """
        result = {}
        for table in self.target.get_table_names():
            var_mappings = {}
            for variable in self.target.get_variable_names(table):
                if not self.variable_should_get_mapped(table, variable):
                    continue
                var_mappings[variable] = self.variable_mappings[table][variable].to_dict()
            result[table] = {'table_mapping' : self.table_mappings[table].to_dict(), 'variable_mappings' : var_mappings}
        return result

    @staticmethod
    def from_dict(input_dict : dict, source: MetaData, target: MetaData) -> 'DataMapping':
        """Reads :class:`~graphxplore.DataMapping.VariableMapping` and :class:`TableMapping` objects from a dictionary
        and combines them with the specified source and target :class:`~graphxplore.MetaDataHandling.MetaData`

        :param input_dict: The input dictionary
        :param source: The metadata of the source dataset
        :param target: The metadata of the target dataset
        :return: Returns a dictionary containing all mappings
        """
        var_mappings = {}
        table_mappings = {}
        for table, table_dict in input_dict.items():
            if 'table_mapping' not in table_dict:
                raise AttributeError('"table_mapping" entry with table mappings for table "' + table + '" missing')
            table_mappings[table] = TableMapping.from_dict(table_dict['table_mapping'])
            if 'variable_mappings' not in table_dict:
                raise AttributeError('"variable_mappings" entry with variable mappings for table "' + table
                                     + '" missing')
            var_mappings[table] = {variable : VariableMapping.from_dict(entry)
                                   for variable, entry in table_dict['variable_mappings'].items()}
        return DataMapping(source, target, table_mappings, var_mappings)

    def to_json(self, json_path : str, file_encoding : Optional[str] = None) -> None:
        """Stores all variable mappings in a JSON

        :param json_path: Path to the JSON
        :param file_encoding: file encoding that should be used for writing the JSON
        """
        dir_path = os.path.dirname(os.path.realpath(json_path))
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            raise AttributeError('File path "' + json_path
                                 + '" is invalid, since the containing directory does not exist')
        output = self.to_dict()
        with open(json_path, "w", encoding=file_encoding) as f:
            json.dump(output, f, indent=6, ensure_ascii=False)

    @staticmethod
    def from_json(json_path : str, source: MetaData, target: MetaData,
                  file_encoding : Optional[str] = None) -> 'DataMapping':
        """Reads :class:`~graphxplore.DataMapping.VariableMapping` and :class:`TableMapping` objects from a JSON
        and combines them with the specified source and target :class:`~graphxplore.MetaDataHandling.MetaData`

        :param json_path: Path to the JSON
        :param source: The metadata of the source dataset
        :param target: The metadata of the target dataset
        :param file_encoding: file encoding of the JSON
        :param file_encoding: file encoding of the JSON
        :return: Returns a dictionary with all mapping data
        """
        if not os.path.isfile(json_path):
            raise AttributeError('Path "' + json_path +'" is not a valid file path')
        encoding = file_encoding if file_encoding is not None else BaseUtils.detect_file_encoding(json_path)
        with open(json_path, encoding=encoding) as f:
            data = json.load(f)
            return DataMapping.from_dict(data, source, target)

    def variable_mapped(self, table: str, variable: str) -> bool:
        """Checks, if at least one :class:`MappingCase` is defined for the table and variable. Raises an exception, if
        the variable and/or table is not present in the mapping

        :param table: The table of the variable to check for
        :param variable: The variable name to check for
        :return: Returns ``True``, if the table and variable exist in the mapping and at least one :class:`MappingCase`
            was defined
        """
        var_mapping = self.get_variable_mapping(table, variable)
        return len(var_mapping.cases) > 0

    def table_fully_mapped(self, table: str) -> bool:
        """Checks, if all variables of a table are mapped, meaning they have at least one :class:`MappingCase`

        :param table: The table to check all variables for
        :return: Returns ``True``, if all variables are mapped
        """
        if table not in self.target.get_table_names():
            raise AttributeError('Table "' + table + '" does not exist in target metadata')
        for variable in self.target.get_variable_names(table):
            if self.variable_should_get_mapped(table, variable) and not self.variable_mapped(table, variable):
                return False
        return True

    def complete(self) -> bool:
        """Checks if all variables of all tables are mapped, meaning they have at least one :class:`MappingCase`

        :return: Returns ``True``, if all variables of all tables are mapped
        """
        for table in self.target.get_table_names():
            if not self.table_fully_mapped(table):
                return False
        return True

    def get_source_tables_for_var_mappings(self, target_table: str,
                                           mapping_to_set : Optional[TableMapping] = None) -> Tuple[List[str], List[str]]:
        """Based on the table mapping of ``target_table``, find all source tables that can be used for variable
        mappings. To cases are possible: Single value conditionals/conclusion (related source tables and foreign
        tables, foreign tables of foreign tables, etc.), and source tables that can be used for aggregation (inverted
        foreign tables of the related source tables, inverted foreign tables of inverted foreign tables, etc.)

        :param target_table: The target table for which available source tables should be retrieved
        :param mapping_to_set: If the table mapping of ``target_table`` is not yet set, you can specify the future
            mapping here. If this parameter is None, the assigned table mapping will be used. Defaults to None
        :return: Returns two lists of source tables, one for single value and one for aggregation conditionals/conclusions
        """
        if target_table not in self.table_mappings:
            raise AttributeError('Target table "' + target_table + '" does not exist in data mapping')
        if mapping_to_set is None:
            table_mapping = self.table_mappings[target_table]
        else:
            table_mapping = mapping_to_set
        if table_mapping.type is None:
            raise AttributeError('Table mapping not yet assigned for target table "' + target_table + '"')
        elif table_mapping.type == TableMappingType.Inherited:
            return self.get_source_tables_for_var_mappings(table_mapping.to_inherit)
        elif table_mapping.type == TableMappingType.OneToOne:
            source_table = table_mapping.source_tables[0]
            upward = set(self.source_lattice.get_relatives(source_table))
            downward = set(self.source_lattice.get_relatives(source_table, False))
            upward_ordered = [table for table in self.source.get_table_names() if table in upward]
            downward_ordered = [table for table in self.source.get_table_names() if table in downward]
            return [source_table] + upward_ordered, downward_ordered
        elif table_mapping.type in [TableMappingType.Merge, TableMappingType.Concatenate]:
            upward = set()
            downward = set()
            for source_table in table_mapping.source_tables:
                upward.update(self.source_lattice.get_relatives(source_table))
                downward.update(self.source_lattice.get_relatives(source_table, False))
            upward_ordered = [table for table in self.source.get_table_names() if
                              table in upward and table not in table_mapping.source_tables]
            downward_ordered = [table for table in self.source.get_table_names() if
                                table in downward and table not in table_mapping.source_tables]
            return table_mapping.source_tables + upward_ordered, downward_ordered
        else:
            raise NotImplementedError('Table mapping type not implemented')
    def _check_table_mapping(self, target_table, table_mapping: TableMapping):
        """Checks the relationship of the given ``target_table`` to the source dataset. It can have a one-to-one
        relation to a single source table, or a one-to-many relation to multiple source tables by merging or
        concatenating their data. Alternatively the type of relation can be inherited from another source table
        which must be an ancestor of ``target_table``.

        :param target_table: The name of the target table
        :param table_mapping: The table mapping to check
        :return: Returns a dictionary with the type of mapping and the relevant source tables
        """
        if table_mapping.type == TableMappingType.OneToOne:
            if len(table_mapping.source_tables) != 1:
                raise AttributeError('One-to-one table mapping need a single source table specified')
        elif table_mapping.type == TableMappingType.Inherited:
            if table_mapping.to_inherit is None:
                raise AttributeError('For inheriting table mapping you need to specify a target table to inherit from')
            if not isinstance(table_mapping.condition, AlwaysTrueOperator):
                raise AttributeError('When inheriting table relation, no condition other than the tautology should be '
                                     'specified')
            if table_mapping.to_inherit not in self.target_lattice.parents[target_table]:
                raise AttributeError('Target table "' + target_table + '" was marked for inheriting from table "'
                                     + table_mapping.to_inherit + '", but "' + target_table
                                     + '" is not a foreign table of "' + table_mapping.to_inherit + '"')
            if self.table_mappings[table_mapping.to_inherit].type is None:
                raise AttributeError('Target table "' + target_table + '" was marked for inheriting from table "'
                                     + table_mapping.to_inherit + '", but this table has no assigned table mapping yet')
        elif table_mapping.type in [TableMappingType.Merge, TableMappingType.Concatenate]:
            if len(table_mapping.source_tables) < 2:
                raise AttributeError('For one-to-many table mappings at least two source tables must be specified')
        for source_table in table_mapping.source_tables:
            if source_table not in self.source.get_table_names():
                raise AttributeError('Source table "' + source_table
                                     + '" was specified in table mapping of target table "' + target_table
                                     + '", but does not exist in source metadata')
            if not isinstance(table_mapping.condition, AlwaysTrueOperator):
                singular_source_tables, aggregation_source_tables = self.get_source_tables_for_var_mappings(
                    target_table, table_mapping)
                self._check_operator_sources(
                    target_table, None, table_mapping.condition, singular_source_tables, aggregation_source_tables)

    def variable_should_get_mapped(self, table: str, variable: str) -> bool:
        """Checks if a variable mapping should be defined for the variable. All variables should be mapped except
        primary keys and foreign keys of foreign tables which inherit the table mapping of ``table``

        :param table: The table of the variable to check
        :param variable: The name of the variable to check
        :return: Returns ``True`` if the variable should have a variable mapping
        """
        if variable == self.target.get_primary_key(table):
            return False
        if variable in self.target.get_foreign_keys(table):
            foreign_table = self.target.get_foreign_keys(table)[variable]
            foreign_table_mapping = self.table_mappings[foreign_table]
            if foreign_table_mapping.type == TableMappingType.Inherited and foreign_table_mapping.to_inherit == table:
                return False
        return True

    @staticmethod
    def _check_operator_sources(table: str, variable: Optional[str], operator: Union[LogicOperator, Conclusion],
                                singular_source_tables: List[str], aggregation_source_tables: List[str]):
        var_string = 'variable mapping of target variable "' + variable + '"' if variable is not None else 'table mapping'
        for source_table, var_data in operator.get_required_data().items():
            for source_var, agg_info in var_data:
                if agg_info is not None:
                    if source_table not in aggregation_source_tables:
                        raise AttributeError('Source table "' + source_table
                                             + '" used for aggregation in ' + var_string + ' in target table "' + table
                                             + '", but cannot be aggregated with specified table mapping')
                else:
                    if source_table not in singular_source_tables:
                        raise AttributeError('Source table "' + source_table
                                             + '" used for singular value comparison in ' + var_string
                                             + ' in target table "' + table
                                             + '", but source table data cannot be used for singular value comparison '
                                               'with specified table mapping')

    def _check_var_mapping(self, var_mapping: VariableMapping, singular_source_tables : List[str],
                           aggregation_source_tables : List[str]):
        table = var_mapping.target_table
        var = var_mapping.target_variable
        var_info = self.target.get_variable(table, var)
        if var_info.variable_type == VariableType.PrimaryKey:
            raise AttributeError('Primary key "' + var + '" of target table "' + table
                                 + '" should not have a variable mapping. The mapping behaviour of primary keys is '
                                   'handled with the table mapping')
        elif var_info.variable_type == VariableType.ForeignKey:
            foreign_table = self.target.get_foreign_keys(table)[var]
            if self.foreign_key_is_for_inheritance(table, var) and len(var_mapping.cases) > 0:
                raise AttributeError('Foreign table "' + foreign_table + '" inherits the table mapping of "'
                                     + table + '", but the foreign key "' + var + '" has mapping cases defined')

        for case in var_mapping.cases:
            for operator in [case.conditional, case.conclusion]:
                self._check_operator_sources(table, var, operator, singular_source_tables, aggregation_source_tables)