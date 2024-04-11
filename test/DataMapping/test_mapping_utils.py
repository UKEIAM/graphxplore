import pytest
import os
import csv
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.MetaDataHandling import MetaData
from graphxplore.DataMapping import DataMappingUtils

BASE_PATH = os.path.dirname(__file__)
SOURCE_DIR = os.path.join(BASE_PATH, 'test_data')
SOURCE_META_PATH = os.path.join(SOURCE_DIR, 'source_meta.json')
OUT_DIR = os.path.join(BASE_PATH, 'test_output', 'util_data_dir')

def test_copy():
    source_meta = MetaData.load_from_json(SOURCE_META_PATH)
    var_info1 = source_meta.get_variable('second_root_table', 'ATTR')
    var_info1.artifacts = ['NaN']
    var_info2 = source_meta.get_variable('third_child_table', 'ATTR')
    var_info2.special_values = {'Na' : 'missing'}

    DataMappingUtils.copy_dataset(source_meta, SOURCE_DIR, OUT_DIR, delete_artifacts=True)

    # unchanged
    with open(os.path.join(OUT_DIR, 'first_root_table.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['PK_ROOT_1', 'ATTR1', 'ATTR2', 'PK_CHILD_1', 'PK_CHILD_2'],
                     ['0', 'SomeText', '42', '0', '0'],
                     ['1', 'SomeText', '17', '1', '1'],
                     ['2', 'AnotherText', '13', '0', '1']]

        assert actual == expected

    with open(os.path.join(OUT_DIR, 'second_root_table.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['PK_ROOT_1', 'ATTR', 'PK_CHILD_1'],
                    ['0', '-1.5', '0'],
                    ['1', '', '1']]

        assert actual == expected

    with open(os.path.join(OUT_DIR, 'third_child_table.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['PK_CHILD_3', 'ATTR'],
                    ['0', '99.0'],
                    ['1', '']]

        assert actual == expected

def test_primary_key_adding():
    target = os.path.join(OUT_DIR, 'pk_added.csv')
    DataMappingUtils.add_primary_key(data_source=SOURCE_DIR, source_table='first_child_table', data_target=OUT_DIR,
                                     target_table='pk_added', primary_key='ADDED_PK', start_idx=42)
    with open(target) as file:
        actual = [line for line in csv.reader(file)]
        expected = [
            ['ADDED_PK', 'PK_CHILD_1' ,'ATTR' ,'PK_CHILD_3'],
            ['42', '0', '0.7', '1'],
            ['43', '1', '2.3', '0']
        ]
        assert actual == expected

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.add_primary_key(data_source=SOURCE_DIR, source_table='invalid',
                                         data_target=OUT_DIR,
                                         target_table='pk_added.csv', primary_key='ADDED_PK', start_idx=42)
    assert str(exc.value) == 'Source table "invalid" does not exist in data source'
    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.add_primary_key(data_source=SOURCE_DIR, source_table='first_child_table',
                                         data_target=OUT_DIR + '_invalid',
                                         target_table='pk_added.csv', primary_key='ADDED_PK', start_idx=42)
    assert str(exc.value) == ('"' + BASE_PATH + '/test_output/util_data_dir_invalid" '
                              'is not a valid directory')

def test_pivot():
    source = [
        {'category' : 'first', 'value' : 'some_value', 'metric' : '0.1'},
        {'category' : 'first', 'value' : '42', 'metric' : '-1.5'},
        {'category' : 'second', 'value' : 'some_value', 'metric' : '0.1'},
        {'category' : 'second', 'value' : '7', 'metric' : '0.7'},
        {'category' : 'third', 'value' : 'some_value', 'metric' : '-1.5'},
    ]

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'invalid', 'invalid')
    assert str(exc.value) == 'Index column "invalid" not found in source table'

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'category', 'invalid')
    assert str(exc.value) == 'Value column "invalid" not found in source table'

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'category', 'category')
    assert str(exc.value) == 'Index column and value column cannot both be "category"'

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'category', 'value', columns_to_keep=['category', 'value', 'metric'])
    assert str(exc.value) == 'Index column "category" in "columns_to_keep", but it will be used for pivotization'

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'category', 'value', columns_to_keep=['value', 'metric'])
    assert str(exc.value) == ('Value column "value" in "columns_to_keep", but it will be used to fill pivot columns in '
                              'result table')

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'category', 'value', columns_to_keep=['metric', 'invalid'])
    assert str(exc.value) == 'Column "invalid" marked for keeping, but not found in source table'

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'category', 'value', to_index={'invalid' : 'invalid_variable'})
    assert str(exc.value) == 'Value to index "invalid" not found in index column "category"'

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'category', 'value', to_index={'some_value' : 'invalid_variable'})
    assert str(exc.value) == 'Value to index "some_value" not found in index column "category"'

    with pytest.raises(AttributeError) as exc:
        DataMappingUtils.pivot_table(source, 'category', 'value', to_index={'first' : 'metric'})
    assert str(exc.value) == 'Index target column name "metric" already existing as column name'

    result = DataMappingUtils.pivot_table(source, 'category', 'value')
    assert result == [
        {'first': 'some_value', 'metric': '0.1', 'second': '', 'third': ''},
        {'first': '42', 'metric': '-1.5', 'second': '', 'third': ''},
        {'first': '', 'metric': '0.1', 'second': 'some_value', 'third': ''},
        {'first': '', 'metric': '0.7', 'second': '7', 'third': ''},
        {'first': '', 'metric': '-1.5', 'second': '', 'third': 'some_value'}
    ]

    result = DataMappingUtils.pivot_table(source, 'category', 'value',
                                          to_index={'first' : 'first_target', 'third' : 'third_target'})
    assert result == [
        {'first_target': 'some_value', 'metric': '0.1', 'third_target': ''},
        {'first_target': '42', 'metric': '-1.5', 'third_target': ''},
        {'first_target': '', 'metric': '-1.5', 'third_target': 'some_value'}
    ]

    result = DataMappingUtils.pivot_table(source, 'category', 'value', columns_to_keep=[],
                                          to_index={'first': 'first_target', 'third': 'third_target'})
    assert result == [
        {'first_target': 'some_value', 'third_target': ''},
        {'first_target': '42', 'third_target': ''},
        {'first_target': '', 'third_target': 'some_value'}
    ]




if __name__ == '__main__':
    pytest.main()