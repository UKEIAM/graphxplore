import itertools
from enum import Enum
from typing import Union, Optional, Iterable

class StringFilterType(str, Enum):
    """The type of filter on attribute nodes with string value.
    """
    Equals = '='
    Contains = 'contains'
    UnequalTo = '<>'

class NumericFilterType(str, Enum):
    """The type of filter on attribute nodes with numeric value.
    """
    Equals = '='
    UnequalTo = '<>'
    Smaller = '<'
    Larger = '>'
    SmallerOrEqual = '<='
    LargerOrEqual = '>='

class AttributeFilter:
    """This class represents one of multiple filters applied to the attribute nodes which are
    :class:`~graphxplore.Basis.BaseNode` objects. A node is valid, if it matches the filter criteria

    :param filter_value: The value against which will be filtered
    :param filter_type: The type of filter
    :param include: If `True`, the filter will be used as whitelist, otherwise as blacklist filter
    """
    def __init__(self, filter_value : Union[str, int, float], filter_type : Union[StringFilterType, NumericFilterType],
                 include : bool):
        if (type(filter_value) == str and not isinstance(filter_type, StringFilterType))\
                or (type(filter_value) != str and isinstance(filter_type, StringFilterType)):
            raise AttributeError('Type of filter value and filter type doe not match')
        self.filter_value = filter_value
        self.type = filter_type
        self.include = include

    def __str__(self):
        if isinstance(self.type, StringFilterType):
            value_string = '"' + str(self.filter_value) + '"'
        else:
            value_string = str(self.filter_value)
        return self.type + ' ' + value_string


class AttributeAssociationGraphPreFilter:
    """This class captures all filters that are applied to the attribute nodes of a
    :class:`~graphxplore.Basis.BaseGraph.BaseGraph` as Neo4J
    database by the :class:`AttributeAssociationGraphGenerator`. Attribute nodes are selected for the statistical
    analysis based on these filters. Each node's `name` and `value` parameter must match at least one whitelist filter
    (if specified) and cannot match a blacklist filter (if specified). With the different table filters the BFS search
    of the :class:`AttributeAssociationGraphGenerator` can be narrowed down, potentially reducing its runtime
    dramatically for large databases.

    :param max_path_length: The maximum allowed length of a path from a primary key node to an attribute node in the BFS
    :param whitelist_tables: If specified, only nodes of these tables and optionally the `target_tables` are traversed
    :param blacklist_tables: If specified, nodes of these tables are enver traversed
    :param target_tables: If specified, only nodes of these tables can be the end of the BFS traversal
        (others can be traversed)
    :param name_filters: The filters on the `name` parameter of the nodes
    :param value_filters: The filters on the `value` parameter of the nodes
    """
    def __init__(self, max_path_length : int = 3, whitelist_tables : Optional[Iterable[str]] = None,
                 blacklist_tables : Optional[Iterable[str]] = None, target_tables : Optional[Iterable[str]] = None,
                 name_filters : Optional[Iterable[AttributeFilter]] = None,
                 value_filters : Optional[Iterable[AttributeFilter]] = None):
        self.max_path_length = max_path_length
        self.table_string  = '|'.join(itertools.chain(('/' + table for table in target_tables or []),
                                                      ('+' + table for table in whitelist_tables or []),
                                                      ('-' + table for table in blacklist_tables or [])))
        if self.table_string != '':
            self.table_string = ', labelFilter: "' + self.table_string + '"'
        self.name_filters = name_filters if name_filters is not None else []
        for name_filter in self.name_filters:
            if not isinstance(name_filter.type, StringFilterType):
                raise AttributeError('Filters for attribute names must be of type string')
        self.value_filters = value_filters if value_filters is not None else []
        self.name_value_filter_str = self.__generate_name_value_filter_string()

    def get_query(self, primary_node_id : int):
        """Generates the Cypher query for the BFS search starting from the primary node with index `primary_node_id`.

        :param primary_node_id: The Neo4j internal node index
        :return: Returns the query as string
        """
        return ('match (r) where id(r) = ' + str(primary_node_id)
                + ' call apoc.path.expandConfig(r, {relationshipFilter: "HAS_ATTR_VAL>|<CONNECTED_TO|ASSIGNED_BIN>" , '
                  'minLevel: 1, uniqueness: "NODE_GLOBAL", maxLevel: ' + str(self.max_path_length) + self.table_string
                + '}) yield path with last(nodes(path)) as n match (n) '
                  'where not exists{(n)-[:ASSIGNED_BIN]->(:AttributeBin)}' + self.name_value_filter_str
                + ' return distinct id(n) as node_id, labels(n) as labels, n.name as name, n.value as value, ' 
                  'n.description as desc, n.refRange as refRange')

    def __generate_name_value_filter_string(self) -> str:
        """Generates the part of the query string for the filter criteria on the `name` and `attribute` node parameters.

        :return: Returns the Cypher query substring for the filtering of `name` and `attribute` node parameters
        """
        name_str = self.__generate_include_exclude_string('n.name', self.name_filters)
        str_filters, num_filters = [], []
        for value_filter in self.value_filters:
            (str_filters if isinstance(value_filter.type, StringFilterType) else num_filters).append(value_filter)
        string_value_str = self.__generate_include_exclude_string('n.value', str_filters)
        if string_value_str != '':
            string_value_str = '(not apoc.meta.isType(n.value, "STRING") or (' + string_value_str + '))'

        numeric_value_str = self.__generate_include_exclude_string('n.value', num_filters)
        if numeric_value_str != '':
            numeric_value_str = '(apoc.meta.isType(n.value, "STRING") or (' + numeric_value_str + '))'
        result = ' and '.join(filter(lambda x : x != '', (name_str, string_value_str, numeric_value_str)))
        return ' and ' + result if result != '' else ''


    @staticmethod
    def __generate_include_exclude_string(literal : str, filters : Iterable[AttributeFilter]) -> str:
        """Split :class:`AttributeFilter` into white and blacklist filters, concatenate each one with "or" clauses and
        combine the two substrings with an "and" clause.

        :param literal: The parameter to filter, should be `n.name` or `n.value`
        :param filters: The filters for which the substring should be generated
        :return: Returns the substring for the Cypher query
        """
        whitelist, blacklist = [], []
        for attr_filter in filters:
            (whitelist if attr_filter.include else blacklist).append(literal + ' ' + str(attr_filter))
        include_str = '(' + ' or '.join(whitelist) + ')' if len(whitelist) > 0 else ''
        exclude_str = 'not (' + ' or '.join(blacklist) + ')' if len(blacklist) > 0 else ''
        return ' and '.join(filter(lambda x: x != '',(include_str, exclude_str)))