import copy
import pytest
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from dataclasses import asdict
from graphxplore.MetaDataHandling import MetaData, VariableInfo, VariableType, DataType

def test_value_casting():
    val = 'someString'
    assert VariableInfo.cast_value(val, DataType.String) == val
    assert VariableInfo.cast_value(val, DataType.Integer) is None
    assert VariableInfo.cast_value(val, DataType.Decimal) is None
    val = '3.5'
    assert VariableInfo.cast_value(val, DataType.String) == val
    assert VariableInfo.cast_value(val, DataType.Integer) is None
    assert VariableInfo.cast_value(val, DataType.Decimal) == 3.5
    val = '42'
    assert VariableInfo.cast_value(val, DataType.String) == val
    assert VariableInfo.cast_value(val, DataType.Integer) == 42
    assert VariableInfo.cast_value(val, DataType.Decimal) == 42.0

def test_var_info_dict_init():
    input_dict = {'invalid_key' : 'invalid_val'}
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Dictionary for variable "var" does not contain an entry "name" of type str'
    input_dict = {'name' : 'otherVar'}
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Variable name "otherVar" in dictionary does not match variable "var"'
    input_dict = {'name': 'var'}
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Dictionary for variable "var" does not contain an entry "table" of type str'
    input_dict['table'] = 42
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Dictionary for variable "var" does not contain an entry "table" of type str'
    input_dict['table'] = 'otherTable'
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Origin table "otherTable" in dictionary for variable "var" does not match table "table"'
    input_dict['table'] = 'table'
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Dictionary for variable "var" does not contain an entry "labels" of type list'
    input_dict['labels'] = ['label']
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == ('Dictionary for variable "var" does not contain an entry "variable_type" of type str, '
                              'VariableType')
    input_dict['variable_type'] = 'invalid'
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == ('Variable type "invalid" invalid, must be "Categorical", "Metric", "PrimaryKey" or '
                              '"ForeignKey"')
    input_dict['variable_type'] = VariableType.PrimaryKey
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == ('Dictionary for variable "var" does not contain an entry "data_type" of type str, '
                              'DataType')
    input_dict['data_type'] = 'invalid'
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Data type "invalid" invalid, must be "String", "Integer" or "Decimal"'
    input_dict['data_type'] = DataType.Integer
    var_info = VariableInfo.from_dict('var', 'table', input_dict)
    actual = var_info.to_dict()
    assert actual == {'artifacts': None,
                      'binning': None,
                      'data_type': 'Integer',
                      'data_type_distribution': None,
                      'default_value': None,
                      'description': None,
                      'labels': ['label'],
                      'name': 'var',
                      'reviewed' : None,
                      'table': 'table',
                      'value_distribution': None,
                      'variable_type': 'PrimaryKey'}

    input_dict['data_type_distribution'] = {'invalid' : 1.0}
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'In data type distribution the key "invalid" was specified, but is not a valid data type'
    input_dict['data_type_distribution'] = {DataType.String : 1.0}
    input_dict['default_value'] = '0.5'
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Default value "0.5" is not of type Integer'
    input_dict['default_value'] = '42'
    input_dict['value_distribution'] = {'invalid' : 'invalid'}
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == ('Value distribution dict not recognized. For metric distributions these keys '
                              'would be required: "median" ,"q1" ,"q3" ,"lower_fence" ,"upper_fence" '
                              ',"outliers" ,"missing_count" ,"artifact_count". For categorical '
                              'distributions these keys would be required: "category_counts" ,"other_count" '
                              ',"missing_count" ,"artifact_count"')
    input_dict['value_distribution'] = {
        'median' : 'invalid',
        'q1' : 1,
        'q3' : 3,
        'lower_fence' : 0,
        'upper_fence' : 4,
        'missing_count' : 5,
        'artifact_count' : 0,
        'outliers' : [-5, 30]
    }
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == ('Value of key "median" in value distribution for variable "var" must be of type int, '
                              'float')
    input_dict['value_distribution'] = {
        'median': 2,
        'q1': 1,
        'q3': 3,
        'lower_fence': 0,
        'upper_fence': 4,
        'missing_count': 5,
        'artifact_count': 0,
        'outliers': [-5, 30]
    }
    binning = {
        'should_bin': True,
        'ref_low' : 0.0
    }
    input_dict['binning'] = binning
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'For variable "var" both or none of reference low and reference high have to be set'
    binning['ref_high'] = -1.0
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'For variable "var" reference low "0.0" is larger than reference high "-1.0"'
    binning['ref_high'] = 90.0
    input_dict['reviewed'] = 'invalid'
    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Dictionary for variable "var" does not contain an entry "reviewed" of type bool, None would also be valid'
    input_dict['reviewed'] = True
    var_info = VariableInfo.from_dict('var', 'table', input_dict)
    actual = var_info.to_dict()
    assert actual == {'artifacts': None,
                      'binning': {'exclude_from_binning': None,
                                  'ref_high': 90.0,
                                  'ref_low': 0.0,
                                  'should_bin': True},
                      'data_type': 'Integer',
                      'data_type_distribution': {'String': 1.0},
                      'default_value': 42,
                      'description': None,
                      'labels': ['label'],
                      'name': 'var',
                      'reviewed': True,
                      'table': 'table',
                      'value_distribution': {'artifact_count': 0,
                                             'lower_fence': 0,
                                             'median': 2,
                                             'missing_count': 5,
                                             'outliers': [-5, 30],
                                             'q1': 1,
                                             'q3': 3,
                                             'upper_fence': 4},
                      'variable_type': 'PrimaryKey'}

    input_dict = {
        'name': 'var',
        'table': 'table',
        'labels': ['label'],
        'data_type': 'String',
        'variable_type': 'Categorical',
        'binning': {'should_bin': True},
    }

    with pytest.raises(AttributeError) as exc:
        VariableInfo.from_dict('var', 'table', input_dict)
    assert str(exc.value) == 'Variable var is marked for binning, but has string type'


def test_metadata():
    meta = MetaData(['first', 'second'])
    assert sorted(meta.get_table_names()) == ['first', 'second']
    with pytest.raises(AttributeError) as exc:
        meta.add_variable('invalid', 'var')
    assert str(exc.value) == 'Table "invalid" not in meta data'
    with pytest.raises(AttributeError) as exc:
        meta.assign_label('first', 'first label')
    assert str(exc.value) == 'Label "first label" should only contain letters, numbers, hyphens and underscores'
    with pytest.raises(AttributeError) as exc:
        meta.assign_label('first', 'first\tlabel')
    assert str(exc.value) == 'Label "first\tlabel" should only contain letters, numbers, hyphens and underscores'
    with pytest.raises(AttributeError) as exc:
        meta.assign_label('first', 'first\nlabel')
    assert str(exc.value) == 'Label "first\nlabel" should only contain letters, numbers, hyphens and underscores'
    meta.assign_label('first', 'first_label')
    meta.assign_label('second', 'second_label')
    meta.add_variable('first', 'first_pk')
    meta.add_variable('first', 'second_pk')
    meta.add_variable('second', 'second_pk')
    with pytest.raises(AttributeError) as exc:
        meta.assign_primary_key('first', 'invalid')
    assert str(exc.value) == 'Primary key "invalid" is not a variable of table "first" in meta data'
    meta.assign_primary_key('first', 'first_pk')
    with pytest.raises(AttributeError) as exc:
        meta.assign_primary_key('first', 'second_pk')
    assert str(exc.value) == 'Primary key already set for table "first"'
    with pytest.raises(AttributeError) as exc:
        meta.add_foreign_key('first', 'second', 'second_pk')
    assert str(exc.value) == 'Foreign key "second_pk" is not primary key in table "second"'
    meta.assign_primary_key('second', 'second_pk')
    meta.add_foreign_key('first', 'second', 'second_pk')
    assert sorted(meta.get_variable_names('first')) == ['first_pk', 'second_pk']
    assert meta.get_foreign_keys('first') == {'second_pk' : 'second'}
    actual = meta.to_dict()
    assert actual == {
        'first': {'foreign_keys': {'second_pk': 'second'},
                  'label': 'first_label',
                  'primary_key': 'first_pk',
                  'variables': {'first_pk': {'artifacts': None,
                                             'binning': None,
                                             'data_type': 'String',
                                             'data_type_distribution': None,
                                             'default_value': None,
                                             'description': None,
                                             'labels': [],
                                             'name': 'first_pk',
                                             'reviewed': None,
                                             'table': 'first',
                                             'value_distribution': None,
                                             'variable_type': 'PrimaryKey'},
                                'second_pk': {'artifacts': None,
                                              'binning': None,
                                              'data_type': 'String',
                                              'data_type_distribution': None,
                                              'default_value': None,
                                              'description': None,
                                              'labels': [],
                                              'name': 'second_pk',
                                              'reviewed': None,
                                              'table': 'first',
                                              'value_distribution': None,
                                              'variable_type': 'ForeignKey'}}},
        'second': {'foreign_keys': {},
                   'label': 'second_label',
                   'primary_key': 'second_pk',
                   'variables': {'second_pk': {'artifacts': None,
                                               'binning': None,
                                               'data_type': 'String',
                                               'data_type_distribution': None,
                                               'default_value': None,
                                               'description': None,
                                               'labels': [],
                                               'name': 'second_pk',
                                               'reviewed': None,
                                               'table': 'second',
                                               'value_distribution': None,
                                               'variable_type': 'PrimaryKey'}}}
    }

    assert MetaData.from_dict(actual).to_dict() == actual

def test_deep_copy():
    first = MetaData(['table1', 'table2'])
    first.add_variable('table1', 'pk1')
    first.assign_primary_key('table1', 'pk1')
    first.add_variable('table2', 'pk2')
    first.assign_primary_key('table2', 'pk2')
    first.add_variable('table2', 'pk1')
    first.add_foreign_key('table2', 'table1', 'pk1')
    second = copy.deepcopy(first)
    assert second.to_dict() == first.to_dict()
    second.assign_label('table1', 'some_label')
    assert first.get_label('table1') == 'table1'
    second.remove_foreign_key('table2', 'pk1')
    assert first.get_foreign_keys('table2') == {'pk1' : 'table1'}
    second.get_variable('table1', 'pk1').data_type = DataType.Integer
    assert first.get_variable('table1', 'pk1').data_type == DataType.String


def test_value_distribution():
    metric = VariableInfo('metric', 'table', ['label'], VariableType.Metric, DataType.Integer)
    vals = {
        '-5' : 1,
        '0' : 2,
        '1' : 5,
        '2' : 7,
        '3' : 9,
        '8' : 1,
        '9' : 1,
        '1000' : 1,
        '9999' : 1,
        '100000000' : 2,
        '' : 3
    }
    metric.detect_artifacts_and_value_distribution(vals)
    assert asdict(metric.value_distribution) == {
        'artifact_count': 5,
        'lower_fence': -2.0,
        'median': 2.5,
        'missing_count': 3,
        'outliers': [8, 9],
        'q1': 1,
        'q3': 3,
        'upper_fence': 6.0
    }
    assert metric.artifacts == ['-5', '1000', '100000000', '9999']
    categorical = VariableInfo('categorical', 'table', ['label'], VariableType.Categorical, DataType.Integer)
    categorical.detect_artifacts_and_value_distribution(vals)
    assert asdict(categorical.value_distribution) == {
        'artifact_count': 0,
        'category_counts': {'-5': 1,
                            '0': 2,
                            '1': 5,
                            '1000': 1,
                            '100000000': 2,
                            '2': 7,
                            '3': 9,
                            '8': 1,
                            '9': 1,
                            '9999': 1},
        'missing_count': 3,
        'other_count': 0}
    assert categorical.artifacts is None
    more_vals = {str(idx) : idx for idx in range(1, 14)}
    categorical.detect_artifacts_and_value_distribution(more_vals)
    assert asdict(categorical.value_distribution) == {
        'artifact_count': 1,
        'category_counts': {'10': 10,
                             '11': 11,
                             '12': 12,
                             '13': 13,
                             '4': 4,
                             '5': 5,
                             '6': 6,
                             '7': 7,
                             '8': 8,
                             '9': 9},
        'missing_count': 0,
        'other_count': 5}
    assert categorical.artifacts == ['1']

    pk = VariableInfo('pk', 'table', ['label'], VariableType.PrimaryKey, DataType.Integer)
    pk.detect_artifacts_and_value_distribution(vals)
    assert pk.value_distribution is None
    assert pk.artifacts is None

    fk = VariableInfo('fk', 'table', ['label'], VariableType.ForeignKey, DataType.Integer)
    fk.detect_artifacts_and_value_distribution(vals)
    assert fk.value_distribution is None
    assert fk.artifacts is None


if __name__ == '__main__':
    pytest.main()
