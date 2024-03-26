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


if __name__ == '__main__':
    pytest.main()