import collections
from typing import Iterable, Dict, List
from graphxplore.MetaDataHandling.meta_data import MetaData

class MetaLattice:
    """This class captures the partial ordering of primary/foreign key relations of tables in a lattice.
    Here, table *y* is a child of  table *x* (and *x* is a parent of *y*) if *x* contains the primary key of *y* as a
    foreign key. This structure is used to efficiently traverse through the relationships of tables within a dataset

    :param children: Direct foreign tables for each table
    """
    def __init__(self, children: Dict[str, List[str]]):
        """Constructor method
        """
        self.min_elements = []
        self.children = dict(children)
        self.parents = {table : [] for table in self.children.keys()}
        self.max_elements = []
        for parent, children in self.children.items():
            if len(children) == 0:
                self.max_elements.append(parent)
            for child in children:
                self.parents[child].append(parent)

        for table, parents in self.parents.items():
            if len(parents) == 0:
                self.min_elements.append(table)

    @staticmethod
    def from_meta_data(meta : MetaData) -> 'MetaLattice':
        """Generate a lattice from the primary/foreign key relations specified in a metadata object

        :param meta: The metadata
        :return: Returns the generated lattice object
        """
        children = collections.defaultdict(list)
        for table in meta.get_table_names():
            table_children = []
            for foreign_table in meta.get_foreign_keys(table).values():
                table_children.append(foreign_table)
            children[table] = table_children

        return MetaLattice(children)

    def get_sub_lattice_whitelist(self, min_tables: Iterable[str], required_tables: Iterable[str]) -> 'MetaLattice':
        """Finds the sub-lattice with the specified ``minimal tables`` containing all required tables.
        All non-related tables of the overall lattice are removed.

        :param min_tables: The minimal tables of the sub-lattice
        :param required_tables: All tables that must be contained in the sub-lattice
        :return: Returns the sub-lattice
        """
        for min_table in min_tables:
            if min_table not in self.children:
                raise AttributeError('Cannot generate sub-lattice, new minimal table "' + min_table +
                                     '" not found in lattice')
        for required in required_tables:
            if required not in self.children:
                raise AttributeError('Cannot generate sub-lattice, required table "' + required +
                                     '" not found in lattice')

        children = collections.defaultdict(list)
        # mark all tables reachable from minimal tables by upward relation
        queue = list(min_tables)
        upwards = set(min_tables)
        while len(queue) > 0:
            current = queue.pop(0)
            for child in self.children[current]:
                if child in min_tables:
                    raise AttributeError('Specified minimal table "' + child
                                         + '" is not minimal, because it is a descendant of one of: "'
                                         + '", "'.join(min_tables) + '"')
                if child not in upwards:
                    queue.append(child)
                    upwards.add(child)
        for required in required_tables:
            if required not in upwards:
                raise AttributeError('Required table "' + required + '" is not related to specified minimal tables ('
                                     + ', '.join(min_tables) + ') using upward foreign key relations in lattice')
            children[required] = []
        # go downward from required tables and add all upward marked tables to sub-lattice
        queue = list(required_tables)
        while len(queue) > 0:
            current = queue.pop(0)
            for parent in self.parents[current]:
                if parent in upwards:
                    if parent not in children:
                        queue.append(parent)
                    children[parent].append(current)

        return MetaLattice(children)

    def get_sub_lattice_blacklist(self, min_tables: Iterable[str], exclude_tables : Iterable[str]) -> 'MetaLattice':
        """Finds the sub-lattice with the specified minimal table, recursively adding children and stopping at the
        specified exclusion tables.

        :param min_tables: The minimal table of the sub-lattice
        :param exclude_tables: Tables that should not be included in the sub-lattice
        :return: Returns the sub-lattice
        """
        for min_table in min_tables:
            if min_table not in self.children:
                raise AttributeError('Cannot generate sub-lattice, new minimal table "' + min_table +
                                     '" not found in lattice')
        children = collections.defaultdict(list)
        # mark all tables reachable from minimal table and stop at blacklist tables
        queue = list(min_tables)
        while len(queue) > 0:
            current = queue.pop(0)
            children[current] = []
            for child in self.children[current]:
                if child in min_tables:
                    raise AttributeError('Specified minimal table "' + child
                                         + '" is not minimal, because it is a descendant of one of: "'
                                         + '", "'.join(min_tables) + '"')
                if child not in exclude_tables:
                    children[current].append(child)
                    if child not in children:
                        queue.append(child)

        return MetaLattice(children)

    def has_multi_reference_relative(self, start_table : str, upward : bool = True) -> bool:
        """Generates the tree of tables related to ``start_table`` by foreign key relation and checks if a table is
        referenced multiple times. This prevents the flattening of the data to the ``start_table`` using the
        :class:`DataFlattener`.

        :param start_table: The start table for the tree
        :param upward: If ``True``, descendants (referenced by `start_table`) are checked. Otherwise, ancestors
            (referencing ``start_table``) are checked. Defaults to ``True``
        :return: Returns ``True`` if a multi reference was found, ``False`` otherwise
        """
        if start_table not in self.children:
            raise AttributeError('Start table "' + start_table
                                 + '" for multiple reference check not contained in lattice')
        queue = [start_table]
        visited = set()
        while len(queue) > 0:
            current = queue.pop(0)
            # found cycle, current is referenced as foreign table in multiple tables related to 'start_table'
            if current in visited:
                return True
            visited.add(current)
            for child in (self.children if upward else self.parents)[current]:
                queue.append(child)
        return False

    def get_ancestor_lattice(self, start_tables: Iterable[str], required_tables: Iterable[str]) -> 'MetaLattice':
        """Generates a sub-lattice, starting from ``start_tables`` and traversing the lattice in reverse order until
        all ``required_tables`` were found. As a result, tables are added to the sub-lattice if they reference members
        of ``start_tables`` as foreign tables or reference foreign tables with that behaviour. All non-related tables of
        the overall lattice are removed.

        :param start_tables: The tables from which the reverse traversal is started
        :param required_tables: All tables that must be contained in the sub-lattice
        :return: Returns the sub-lattice
        """
        for start_table in start_tables:
            if start_table not in self.children:
                raise AttributeError('Cannot generate inverted lattice, start table "' + start_table +
                                     '" not found in lattice')
        for required in required_tables:
            if required not in self.children:
                raise AttributeError('Cannot generate inverted lattice, required table "' + required +
                                     '" not found in lattice')

        sub_children = collections.defaultdict(list)
        # mark all tables reachable from minimal tables by downward relation
        queue = list(start_tables)
        downwards = set()
        while len(queue) > 0:
            current = queue.pop(0)
            downwards.add(current)
            for parent in self.parents[current]:
                if parent in start_tables:
                    raise AttributeError('Specified start table "' + parent
                                         + '" is not maximal, because it is an ancestor of one of: "'
                                         + '", "'.join(start_tables) + '"')
                if parent not in downwards:
                    queue.append(parent)
        for required in required_tables:
            if required not in downwards:
                raise AttributeError('Required table "' + required + '" is not related to specified minimal tables ('
                                     + ', '.join(start_tables) + ') using downward foreign key relations in lattice')
            sub_children[required] = []
        # go upward from required tables and add all downward marked tables to sub-lattice
        queue = list(required_tables)
        while len(queue) > 0:
            current = queue.pop(0)
            for child in self.children[current]:
                if child in downwards:
                    if child not in sub_children:
                        sub_children[child] = []
                        queue.append(child)
                    sub_children[current].append(child)

        return MetaLattice(sub_children)

    def get_relatives(self, start_table : str, upward : bool = True) -> List[str]:
        """Finds all upward or downward relatives of ``start_table`` in the lattice (excluding ``start_table`` itself).

        :param start_table: The table for which the relatives should be found
        :param upward: If ``True`` upward foreign table relations are considered, else downward (inverted) relations
        :return: Returns the list of relative tables
        """
        if start_table not in self.children:
            raise AttributeError('Cannot find relatives, start table "' + start_table + '" not found in lattice')
        queue = [start_table]
        result = set()
        traversal = (self.children if upward else self.parents)
        while len(queue) > 0:
            curr_table = queue.pop(0)
            for next_table in traversal[curr_table]:
                if next_table not in result:
                    result.add(next_table)
                    queue.append(next_table)
        return list(result)

    def get_sub_lattice_from_inheritance(self, start_table : str, inheriting_tables : Dict[str, str]) -> 'MetaLattice':
        """Get the sub-lattice of all tables directly or indirectly inheriting the relation to the source dataset from
        ``start_table``. If no table inherits from ``start_table``, it will be the only table in the sub-lattice

        :param start_table: The table from which all others of the sub-lattice inherit
        :param inheriting_tables: Dictionary of all inheriting tables and the table they directly inherit from
        :return: Returns the generated sub-lattice
        """
        if start_table not in self.children:
            raise AttributeError('Cannot find relatives, start table "' + start_table + '" not found in lattice')
        queue = [start_table]
        sub_children = {}
        upwards = set()
        while len(queue) > 0:
            curr_table = queue.pop(0)
            if curr_table not in sub_children:
                sub_children[curr_table] = []
            for next_table in self.children[curr_table]:
                if next_table in inheriting_tables and inheriting_tables[next_table] in sub_children:
                    sub_children[curr_table].append(next_table)
                    if next_table not in upwards:
                        upwards.add(next_table)
                        queue.append(next_table)
        return MetaLattice(sub_children)

    def get_shortest_paths_to_required(self, start_table : str, required_tables : Iterable[str]) -> Dict[str, List[str]]:
        """Detects the shortest path from ``start_table`` through the lattice to all tables in ``required_tables``
        individually. A BFS strategy with parent storage is applied.

        :param start_table: The starting table of the paths
        :param required_tables: The tables for which the paths to the root should be calculated
        :return: Returns a dictionary containing the shortest path as list starting from ``start_table`` for each table
            in ``required_tables``
        """
        if start_table not in self.children:
            raise AttributeError('Cannot find shortest path, start table "' + start_table + '" not found in lattice')
        for required in required_tables:
            if required not in self.children:
                raise AttributeError(
                    'Cannot find shortest path to table "' + required + '", since not found in lattice')
        queue = [start_table]
        parents = {start_table : None}
        while len(queue) > 0:
            curr_table = queue.pop(0)
            for next_table in self.children[curr_table]:
                if next_table not in parents:
                    queue.append(next_table)
                    parents[next_table] = curr_table

        result = {}
        for required in required_tables:
            if required not in parents:
                raise AttributeError(
                    'No path exists from start table "' + start_table + '" to table "' + required + '" in lattice')
            path = []
            current = required
            while current is not None:
                path.append(current)
                current = parents[current]
            path.reverse()
            result[required] = path
        return result
