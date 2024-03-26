import pytest
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.MetaDataHandling import DataType
from graphxplore.DataMapping.Conclusions import CopyConclusion, FixedReturnConclusion, AggregateConclusion
from graphxplore.DataMapping import AggregatorType

def test_conclusions():
    # copy
    expected_conclusion = CopyConclusion(DataType.String, 'table', 'var')
    control_str = 'COPY VARIABLE var IN TABLE table IF TYPE IS String'
    assert str(expected_conclusion) == control_str
    expected_conclusion = CopyConclusion.from_string(control_str)
    assert str(expected_conclusion) == control_str
    assert expected_conclusion.get_required_data() == {'table' : [('var', None)]}

    # fixed return
    expected_conclusion = FixedReturnConclusion(DataType.Decimal, 15)
    control_str = 'RETURN 15.0 OF TYPE Decimal'
    assert str(expected_conclusion) == control_str
    expected_conclusion = FixedReturnConclusion.from_string(control_str)
    assert str(expected_conclusion) == control_str
    assert expected_conclusion.get_required_data() == {}

def test_aggregate_conclusions():
    conclusion = AggregateConclusion(DataType.Integer, 'origin_table', 'var', AggregatorType.Min)
    expected = 'AGGREGATE MIN VARIABLE var OF TYPE Integer IN TABLE origin_table'
    assert str(conclusion) == expected
    conclusion = AggregateConclusion.from_string(expected)
    assert conclusion.target_data_type == DataType.Decimal
    assert conclusion.source_data_type == DataType.Integer
    assert str(conclusion) == expected
    assert conclusion.get_required_data() == {'origin_table': [('var', (AggregatorType.Min, DataType.Integer))]}
    with pytest.raises(AttributeError) as exc:
        AggregateConclusion(DataType.String, 'origin_table', 'var', AggregatorType.Median)
    assert str(exc.value) == ('The aggregator type "MEDIAN" is invalid for string value aggregation of '
                              'variable "var" of table "origin_table". Possible aggregator types are: '
                              '"CONCATENATE", "COUNT"')
    conclusion = AggregateConclusion(DataType.Integer, 'origin_table', 'var', AggregatorType.Amplitude)
    expected = 'AGGREGATE AMPLITUDE VARIABLE var OF TYPE Integer IN TABLE origin_table'
    assert str(conclusion) == expected

if __name__ == '__main__':
    pytest.main()