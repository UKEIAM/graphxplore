import pytest
import os
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.DataMapping import MetaLattice
from graphxplore.MetaDataHandling import MetaData

def test_lattice():
    meta_path = os.path.join(os.path.dirname(__file__), 'test_data', 'source_meta.json')
    source_meta = MetaData.load_from_json(meta_path)
    lattice = MetaLattice.from_meta_data(source_meta)
    assert sorted(lattice.min_elements) == ['first_root_table', 'second_root_table']

    expected_children = {
        'first_root_table' : ['first_child_table', 'second_child_table'],
        'second_root_table': ['first_child_table'],
        'first_child_table' : ['third_child_table'],
        'second_child_table' : [],
        'third_child_table' : []
    }
    actual_children = {key : list(value) for key, value in lattice.children.items()}
    assert actual_children == expected_children
    expected_parents = {
        'first_root_table': [],
        'second_root_table': [],
        'first_child_table': ['first_root_table', 'second_root_table'],
        'second_child_table': ['first_root_table'],
        'third_child_table': ['first_child_table']
    }
    assert lattice.parents == expected_parents

    # sub-lattice whitelist

    with pytest.raises(AttributeError) as exc:
        lattice.get_sub_lattice_whitelist(['first_child_table'], ['first_child_table', 'second_child_table'])
    assert str(exc.value) == ('Required table "second_child_table" is not related to specified minimal '
                               'tables (first_child_table) using upward foreign key relations in lattice')

    sub_lattice = lattice.get_sub_lattice_whitelist(['first_child_table'], ['first_child_table', 'third_child_table'])
    expected_children = {
        'first_child_table': ['third_child_table'],
        'third_child_table': []
    }
    actual_children = {key: list(value) for key, value in sub_lattice.children.items()}
    assert actual_children == expected_children
    expected_parents = {
        'first_child_table': [],
        'third_child_table': ['first_child_table']
    }
    assert sub_lattice.parents == expected_parents
    expected_leaves = ['third_child_table']
    assert sub_lattice.max_elements == expected_leaves

    smaller_sub_lattice = lattice.get_sub_lattice_whitelist(['first_child_table'], ['first_child_table'])
    expected_children = {
        'first_child_table': []
    }
    actual_children = {key: list(value) for key, value in smaller_sub_lattice.children.items()}
    assert actual_children == expected_children
    expected_parents = {
        'first_child_table': []
    }
    assert smaller_sub_lattice.parents == expected_parents
    expected_leaves = ['first_child_table']
    assert smaller_sub_lattice.max_elements == expected_leaves

    #  sub-lattice blacklist
    blacklist_tables = ['second_child_table']
    sub_lattice = lattice.get_sub_lattice_blacklist(['first_root_table'], blacklist_tables)
    expected_children = {
        'first_root_table': ['first_child_table'],
        'first_child_table': ['third_child_table'],
        'third_child_table': []
    }
    actual_children = {key: list(value) for key, value in sub_lattice.children.items()}
    assert actual_children == expected_children
    expected_parents = {
        'first_root_table': [],
        'first_child_table': ['first_root_table'],
        'third_child_table': ['first_child_table']
    }
    assert sub_lattice.parents == expected_parents
    expected_leaves = ['third_child_table']
    assert sub_lattice.max_elements == expected_leaves

    children = {
        'first_root_table' : ['first_child_table'],
        'second_root_table': ['first_child_table'],
        'first_child_table' : ['third_child_table', 'second_child_table'],
        'second_child_table' : [],
        'third_child_table' : []
    }

    lattice = MetaLattice(children)

    full_lattice = lattice.get_sub_lattice_whitelist(['first_root_table', 'second_root_table'],
                                                     ['third_child_table', 'second_child_table'])

    assert full_lattice.children == children

def test_multi_reference():
    children = {
        'min_1' : ['child_1'],
        'min_2' : ['child_1'],
        'child_1' : ['child_2'],
        'child_2' : []
    }

    # the lattice itself has multi reference of 'child_1', but from different minimal elements
    lattice = MetaLattice(children)
    assert not lattice.has_multi_reference_relative('min_1', upward=True)
    assert not lattice.has_multi_reference_relative('child_2', upward=False)
    children['min_1'].append('child_2')
    invalid_lattice = MetaLattice(children)
    assert not invalid_lattice.has_multi_reference_relative('min_2', upward=True)
    assert invalid_lattice.has_multi_reference_relative('min_1', upward=True)
    assert invalid_lattice.has_multi_reference_relative('child_2', upward=False)

def test_inverted_lattice():
    children = {
        'first_root_table': ['first_child_table', 'second_child_table'],
        'second_root_table': ['first_child_table'],
        'first_child_table': ['third_child_table'],
        'second_child_table': [],
        'third_child_table': []
    }
    lattice = MetaLattice(children)
    with pytest.raises(AttributeError) as exc:
        lattice.get_ancestor_lattice(['invalid'], ['invalid_req'])
    assert str(exc.value) == 'Cannot generate inverted lattice, start table "invalid" not found in lattice'

    with pytest.raises(AttributeError) as exc:
        lattice.get_ancestor_lattice(['third_child_table'], ['invalid_req'])
    assert str(exc.value) == 'Cannot generate inverted lattice, required table "invalid_req" not found in lattice'

    ancestor_lattice = lattice.get_ancestor_lattice(['third_child_table'], ['first_root_table', 'second_root_table'])

    assert ancestor_lattice.children == {
        'first_root_table': ['first_child_table'],
        'second_root_table': ['first_child_table'],
        'first_child_table': ['third_child_table'],
        'third_child_table': []
    }

    ancestor_lattice = lattice.get_ancestor_lattice(['third_child_table'], ['first_root_table'])

    assert ancestor_lattice.children == {
        'first_root_table': ['first_child_table'],
        'first_child_table': ['third_child_table'],
        'third_child_table': []
    }

    ancestor_lattice = lattice.get_ancestor_lattice(['third_child_table', 'second_child_table'], ['first_root_table'])

    assert ancestor_lattice.children == {
        'first_root_table': ['first_child_table', 'second_child_table'],
        'first_child_table': ['third_child_table'],
        'third_child_table': [],
        'second_child_table': []
    }

    ancestor_lattice = lattice.get_ancestor_lattice(['third_child_table', 'second_child_table'],
                                                    ['first_root_table', 'second_root_table'])

    assert ancestor_lattice.children == children

def test_non_minimal_children():
    children = {
        'first_root_table': ['first_child_table', 'second_child_table'],
        'second_root_table': ['first_child_table'],
        'first_child_table': ['third_child_table'],
        'second_child_table': [],
        'third_child_table': []
    }
    lattice = MetaLattice(children)
    with pytest.raises(AttributeError) as exc:
        lattice.get_sub_lattice_whitelist(['first_root_table', 'first_child_table'],
                                          ['first_root_table', 'first_child_table'])
    assert str(exc.value) == ('Specified minimal table "first_child_table" is not minimal, because it is a '
                              'descendant of one of: "first_root_table", "first_child_table"')
    with pytest.raises(AttributeError) as exc:
        lattice.get_sub_lattice_blacklist(['first_root_table', 'first_child_table'],
                                          ['second_child_table'])
    assert str(exc.value) == ('Specified minimal table "first_child_table" is not minimal, because it is a '
                              'descendant of one of: "first_root_table", "first_child_table"')

    with pytest.raises(AttributeError) as exc:
        lattice.get_ancestor_lattice(['third_child_table', 'first_child_table'], ['first_root_table'])
    assert str(exc.value) == ('Specified start table "first_child_table" is not maximal, because it is an '
                              'ancestor of one of: "third_child_table", "first_child_table"')

def test_sub_lattice_from_inheritance():
    children = {
        'first_root_table': ['first_child_table', 'second_child_table'],
        'second_root_table': ['first_child_table'],
        'first_child_table': ['third_child_table'],
        'second_child_table': ['third_child_table'],
        'third_child_table': ['fourth_child_table'],
        'fourth_child_table' : []
    }
    lattice = MetaLattice(children)
    inheriting_tables = {
        'first_child_table' : 'first_root_table',
        'second_child_table' : 'first_root_table',
        'third_child_table' : 'first_child_table',
        'fourth_child_table' : 'third_child_table'
    }
    sub_lattice = lattice.get_sub_lattice_from_inheritance('first_root_table', inheriting_tables)
    # inheritance from second to third not marked, but must still be inferred
    assert sub_lattice.children == {
        'first_root_table': ['first_child_table', 'second_child_table'],
        'first_child_table': ['third_child_table'],
        'second_child_table' : ['third_child_table'],
        'third_child_table': ['fourth_child_table'],
        'fourth_child_table' : []
    }

if __name__ == '__main__':
    pytest.main()