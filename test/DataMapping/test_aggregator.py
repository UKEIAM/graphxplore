import pytest
import os
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.MetaDataHandling import MetaData, DataType
from graphxplore.DataMapping import AggregatorType, MetaLattice, CSVDataAggregator, AggregatedData

BASE_PATH = os.path.dirname(__file__)

SOURCE_DIR = os.path.join(BASE_PATH, 'test_data')
SOURCE_META_PATH = os.path.join(BASE_PATH, 'test_data', 'source_meta.json')

def test_data_aggregation():
    meta = MetaData.load_from_json(SOURCE_META_PATH)
    overall_lattice = MetaLattice.from_meta_data(meta)
    sub_lattice = overall_lattice.get_ancestor_lattice(['first_child_table'], required_tables=['first_root_table',
                                                                                               'second_root_table'])
    required_vars = {'first_root_table' : {
        'ATTR1' : [
            (AggregatorType.Count, DataType.String),
            (AggregatorType.Count, DataType.Integer),
            (AggregatorType.List, DataType.String)
        ],
        'ATTR2': [
            (AggregatorType.Count, DataType.Decimal),
            (AggregatorType.Min, DataType.Integer),
            (AggregatorType.Max, DataType.Integer),
            (AggregatorType.Mean, DataType.Integer),
            (AggregatorType.Median, DataType.Integer),
            (AggregatorType.Std, DataType.Integer),
            (AggregatorType.Sum, DataType.Integer),
            (AggregatorType.Amplitude, DataType.Integer)
        ]
    },
    'second_root_table' : {
        'ATTR' : [
            (AggregatorType.Count, DataType.Decimal),
            (AggregatorType.Median, DataType.Decimal)
        ]
    }}

    aggregator = CSVDataAggregator(SOURCE_DIR, meta, sub_lattice, required_vars)
    aggregator.aggregate_data()
    actual_pks = sorted(aggregator.aggregated_data['first_child_table'].keys())
    assert actual_pks == ['0', '1']
    first_aggregated = aggregator.aggregated_data['first_child_table']['0']
    with pytest.raises(AttributeError) as exc:
        first_aggregated.get_variable_aggregation('invalid', 'invalid', DataType.Decimal, AggregatorType.Count)
    assert str(exc.value) == 'Table "invalid" not found in aggregated source data'
    with pytest.raises(AttributeError) as exc:
        first_aggregated.get_variable_aggregation('first_root_table', 'invalid', DataType.Decimal, AggregatorType.Count)
    assert str(exc.value) == 'Variable "invalid" for table "first_root_table" not found in aggregated source data'
    with pytest.raises(AttributeError) as exc:
        first_aggregated.get_variable_aggregation('first_root_table', 'ATTR1', DataType.Decimal, AggregatorType.Count)
    assert str(exc.value) == ('Aggregated data of type "COUNT" for values of data type "Decimal" of '
                              'variable "ATTR1" in table "first_root_table" does not exist in aggregated source data')

    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR1', DataType.String,
                                                      AggregatorType.Count) == 2
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR1', DataType.Integer,
                                                     AggregatorType.Count) == 0
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR1', DataType.String,
                                                     AggregatorType.List) == {'SomeText', 'AnotherText'}

    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR2', DataType.Decimal,
                                                     AggregatorType.Count) == 2
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR2', DataType.Integer,
                                                     AggregatorType.Min) == 13
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR2', DataType.Integer,
                                                     AggregatorType.Max) == 42
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR2', DataType.Integer,
                                                     AggregatorType.Sum) == 55
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR2', DataType.Integer,
                                                     AggregatorType.Amplitude) == 29
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR2', DataType.Integer,
                                                     AggregatorType.Mean) == 27.5
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR2', DataType.Integer,
                                                     AggregatorType.Std) == 14.5
    assert first_aggregated.get_variable_aggregation('first_root_table', 'ATTR2', DataType.Integer,
                                                     AggregatorType.Median) == 27.5

    assert first_aggregated.get_variable_aggregation('second_root_table', 'ATTR', DataType.Decimal,
                                                     AggregatorType.Median) == -1.5

    second_aggregated = aggregator.aggregated_data['first_child_table']['1']
    assert second_aggregated.get_variable_aggregation('second_root_table', 'ATTR', DataType.Decimal,
                                                     AggregatorType.Median) is None
    assert second_aggregated.get_variable_aggregation('second_root_table', 'ATTR', DataType.Decimal,
                                                      AggregatorType.Count) == 0


def test_aggregated_data_merging():
    first = AggregatedData()
    first.aggregated_data['table'] = {'var' : {(DataType.String, AggregatorType.Count) : 42}}
    second = AggregatedData()
    second.aggregated_data['otherTable'] = {'var': {(DataType.String, AggregatorType.Count): 42}}
    expected = {
        'table' : {'var' : {(DataType.String, AggregatorType.Count) : 42}},
        'otherTable' : {'var' : {(DataType.String, AggregatorType.Count) : 42}}
    }
    assert first.merge(second).aggregated_data == expected

    second.aggregated_data = {'table' : {'otherVar' : {(DataType.String, AggregatorType.Count) : 42}}}
    expected = {
        'table': {
            'var': {(DataType.String, AggregatorType.Count): 42},
            'otherVar': {(DataType.String, AggregatorType.Count): 42}
        }
    }
    assert first.merge(second).aggregated_data == expected
    second.aggregated_data = {'table': {'var': {
        (DataType.Integer, AggregatorType.Count): 42}}}
    expected = {
        'table': {
            'var': {(DataType.Integer, AggregatorType.Count): 42,
                    (DataType.String, AggregatorType.Count) : 42}
        }
    }
    assert first.merge(second).aggregated_data == expected
    second.aggregated_data = {'table': {'var': {
        (DataType.String, AggregatorType.Count): None}}}
    expected = {
        'table': {
            'var': {(DataType.String, AggregatorType.Count): 42}
        }
    }
    assert first.merge(second).aggregated_data == expected
    first.aggregated_data = {'table': {'var': {
        (DataType.String, AggregatorType.Count): None}}}
    second.aggregated_data = {'table': {'var': {
        (DataType.String, AggregatorType.Count): 42}}}
    expected = {
        'table': {
            'var': {(DataType.String, AggregatorType.Count): 42}
        }
    }
    assert first.merge(second).aggregated_data == expected
    first.aggregated_data = {'table': {'var': {
        (DataType.String, AggregatorType.Count): 1337}}}
    with pytest.raises(AttributeError) as exc:
        first.merge(second)
    assert str(exc.value) == ('Cannot merge aggregated data objects, because aggregated data for variable '
                              '"var" of table "table", data type String and aggregation type COUNT is '
                              'contained in both objects and values differ')

if __name__ == '__main__':
    pytest.main()