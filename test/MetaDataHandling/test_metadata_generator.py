import collections
import json
import os
import pytest
import pathlib
import csv
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.MetaDataHandling import MetaDataGenerator, VariableType, DataType, ArtifactMode

BASE_PATH = os.path.dirname(__file__)

def test_meta_extraction():
    data_dir = os.path.join(BASE_PATH, 'test_data')
    descriptions = {
        "primary_table" : {
            "ROW_ID" : "irrelevant index",
            "PRIMARY" : "primary key",
            "STRING_ATTR" : "contains text"
        },
         "secondary_table" : {
            "OWN_PRIMARY" : "primary key",
            "PRIMARY" : "is foreign key",
            "ATTR_WITH_EMPTY" : "weird variable"
         }
    }

    csv_data = {}
    for csv_table in os.listdir(data_dir):
        if csv_table.endswith('.csv'):
            with open(os.path.join(data_dir, csv_table)) as file:
                reader = csv.DictReader(file)
                csv_data[csv_table.replace('.csv', '')] = [line for line in reader]

    m_handler = MetaDataGenerator(data_dir, artifact_mode=ArtifactMode.NoArtifacts)

    m_handler.gather_meta_data()
    result = m_handler.result
    for table, var_desc_dict in descriptions.items():
        for var, desc in var_desc_dict.items():
            result.get_variable(table, var).description = desc
    vanilla_dict = result.to_dict()
    var_info = result.get_variable('primary_table', 'FLOAT_ATTR')
    var_info.binning.should_bin = True
    var_info.binning.exclude_from_binning = [-1.0, 'na']
    var_info.binning.ref_low = 0.0
    var_info.binning.ref_high = 0.5
    var_info = result.get_variable('secondary_table', 'ATTR_WITH_EMPTY')
    var_info.default_value = "default value"
    assert result.get_primary_key('primary_table') == 'ROW_ID'
    assert result.get_foreign_keys('secondary_table') == {}
    with pytest.raises(AttributeError) as exc:
        result.assign_primary_key('primary_table', 'PRIMARY')
    assert str(exc.value) == 'Primary key already set for table "primary_table"'
    result.change_primary_key('primary_table', 'PRIMARY')
    result.add_foreign_key('secondary_table', 'primary_table', 'PRIMARY')
    row_id_var_info = result.get_variable('primary_table', 'ROW_ID')
    var_info_float = result.get_variable('primary_table', 'FLOAT_ATTR')
    var_info_float.variable_type = VariableType.Metric
    var_info_float.artifacts = None
    var_info_mixed = result.get_variable('primary_table', 'MIXED_ATTR')
    var_info_mixed.data_type = DataType.Decimal
    var_info_mixed.variable_type = VariableType.Metric
    var_info_mixed.artifacts = None
    var_float_data_dict = collections.defaultdict(int)
    var_mixed_data_dict = collections.defaultdict(int)
    row_id_data_dict = collections.defaultdict(int)
    for row in csv_data['primary_table']:
        var_float_data_dict[row['FLOAT_ATTR']] += 1
        var_mixed_data_dict[row['MIXED_ATTR']] += 1
        row_id_data_dict[row['ROW_ID']] += 1
    var_info_float.detect_artifacts_and_value_distribution(var_float_data_dict)
    var_info_mixed.detect_artifacts_and_value_distribution(var_mixed_data_dict)
    row_id_var_info.detect_artifacts_and_value_distribution(
        row_id_data_dict, artifact_mode=ArtifactMode.OnlyDataTypeMismatch)
    assert var_info_float.artifacts == ['3000.6']
    assert var_info_mixed.artifacts == ['Text']
    assert row_id_var_info.artifacts is None

    meta_path = os.path.join(BASE_PATH, 'test_output', 'meta.json')
    result.store_in_json(meta_path)
    with open(meta_path) as file:
        actual = json.load(file)
        expected = {'primary_table': {'foreign_keys': {},
                   'label': 'primary_table',
                   'primary_key': 'PRIMARY',
                   'variables': {'FLOAT_ATTR': {'artifacts': ['3000.6'],
                                                'binning': {'exclude_from_binning': [-1.0,
                                                                                     'na'],
                                                            'ref_high': 0.5,
                                                            'ref_low': 0.0,
                                                            'should_bin': True},
                                                'data_type': 'Decimal',
                                                'data_type_distribution': {'Decimal': 1.0,
                                                                           'Integer': 0.0,
                                                                           'String': 0.0},
                                                'default_value': None,
                                                'description': None,
                                                'labels': [],
                                                'name': 'FLOAT_ATTR',
                                                'reviewed': None,
                                                'table': 'primary_table',
                                                'value_distribution': {'artifact_count': 1,
                                                                       'lower_fence': 0.5,
                                                                       'median': 1.0,
                                                                       'missing_count': 0,
                                                                       'outliers': [],
                                                                       'q1': 0.5,
                                                                       'q3': 2.0,
                                                                       'upper_fence': 4.25},
                                                'variable_type': 'Metric'},
                                 'MIXED_ATTR': {'artifacts': ['Text'],
                                                'binning': {'exclude_from_binning': None,
                                                            'ref_high': None,
                                                            'ref_low': None,
                                                            'should_bin': False},
                                                'data_type': 'Decimal',
                                                'data_type_distribution': {'Decimal': 0.4,
                                                                           'Integer': 0.2,
                                                                           'String': 0.4},
                                                'default_value': None,
                                                'description': None,
                                                'labels': [],
                                                'name': 'MIXED_ATTR',
                                                'reviewed': None,
                                                'table': 'primary_table',
                                                'value_distribution': {'artifact_count': 2,
                                                                       'lower_fence': 0.2,
                                                                       'median': 0.2,
                                                                       'missing_count': 0,
                                                                       'outliers': [],
                                                                       'q1': 0.2,
                                                                       'q3': 2.0,
                                                                       'upper_fence': 2.0},
                                                'variable_type': 'Metric'},
                                 'PRIMARY': {'artifacts': None,
                                             'binning': {'exclude_from_binning': None,
                                                         'ref_high': None,
                                                         'ref_low': None,
                                                         'should_bin': False},
                                             'data_type': 'Integer',
                                             'data_type_distribution': {'Decimal': 0.0,
                                                                        'Integer': 1.0,
                                                                        'String': 0.0},
                                             'default_value': None,
                                             'description': 'primary key',
                                             'labels': [],
                                             'name': 'PRIMARY',
                                             'reviewed': None,
                                             'table': 'primary_table',
                                             'value_distribution': {'artifact_count': 0,
                                                                    'category_counts': {'1': 1,
                                                                                        '2': 1,
                                                                                        '3': 1,
                                                                                        '4': 1,
                                                                                        '5': 1},
                                                                    'missing_count': 0,
                                                                    'other_count': 0},
                                             'variable_type': 'PrimaryKey'},
                                 'ROW_ID': {'artifacts': None,
                                            'binning': None,
                                            'data_type': 'Integer',
                                            'data_type_distribution': {'Decimal': 0.0,
                                                                       'Integer': 1.0,
                                                                       'String': 0.0},
                                            'default_value': None,
                                            'description': 'irrelevant index',
                                            'labels': [],
                                            'name': 'ROW_ID',
                                            'reviewed': None,
                                            'table': 'primary_table',
                                            'value_distribution': {'artifact_count': 0,
                                                                   'category_counts': {'0': 1,
                                                                                       '1': 1,
                                                                                       '2': 1,
                                                                                       '3': 1,
                                                                                       '4': 1},
                                                                   'missing_count': 0,
                                                                   'other_count': 0},
                                            'variable_type': 'Categorical'},
                                 'STRING_ATTR': {'artifacts': None,
                                                 'binning': {'exclude_from_binning': None,
                                                             'ref_high': None,
                                                             'ref_low': None,
                                                             'should_bin': False},
                                                 'data_type': 'String',
                                                 'data_type_distribution': {'Decimal': 0.0,
                                                                            'Integer': 0.0,
                                                                            'String': 1.0},
                                                 'default_value': None,
                                                 'description': 'contains text',
                                                 'labels': [],
                                                 'name': 'STRING_ATTR',
                                                 'reviewed': None,
                                                 'table': 'primary_table',
                                                 'value_distribution': {'artifact_count': 0,
                                                                        'category_counts': {'AnotherText\nMoreText': 1,
                                                                                            'Text': 3,
                                                                                            'TextWithoutQuotes': 1},
                                                                        'missing_count': 0,
                                                                        'other_count': 0},
                                                 'variable_type': 'Categorical'}}},
 'secondary_table': {'foreign_keys': {'PRIMARY': 'primary_table'},
                     'label': 'secondary_table',
                     'primary_key': 'OWN_PRIMARY',
                     'variables': {'ATTR_WITH_EMPTY': {'artifacts': None,
                                                       'binning': {'exclude_from_binning': None,
                                                                   'ref_high': None,
                                                                   'ref_low': None,
                                                                   'should_bin': False},
                                                       'data_type': 'String',
                                                       'data_type_distribution': {'Decimal': 0.0,
                                                                                  'Integer': 0.0,
                                                                                  'String': 1.0},
                                                       'default_value': 'default '
                                                                        'value',
                                                       'description': 'weird '
                                                                      'variable',
                                                       'labels': [],
                                                       'name': 'ATTR_WITH_EMPTY',
                                                       'reviewed': None,
                                                       'table': 'secondary_table',
                                                       'value_distribution': {'artifact_count': 0,
                                                                              'category_counts': {'NotEmpty': 2},
                                                                              'missing_count': 2,
                                                                              'other_count': 0},
                                                       'variable_type': 'Categorical'},
                                   'FLOAT_INT_ATTR': {'artifacts': None,
                                                      'binning': {'exclude_from_binning': None,
                                                                  'ref_high': None,
                                                                  'ref_low': None,
                                                                  'should_bin': False},
                                                      'data_type': 'Decimal',
                                                      'data_type_distribution': {'Decimal': 0.25,
                                                                                 'Integer': 0.75,
                                                                                 'String': 0.0},
                                                      'default_value': None,
                                                      'description': None,
                                                      'labels': [],
                                                      'name': 'FLOAT_INT_ATTR',
                                                      'reviewed': None,
                                                      'table': 'secondary_table',
                                                      'value_distribution': {'artifact_count': 0,
                                                                             'category_counts': {'1': 1,
                                                                                                 '1.01': 1,
                                                                                                 '2': 2},
                                                                             'missing_count': 0,
                                                                             'other_count': 0},
                                                      'variable_type': 'Categorical'},
                                   'OWN_PRIMARY': {'artifacts': None,
                                                   'binning': None,
                                                   'data_type': 'Integer',
                                                   'data_type_distribution': {'Decimal': 0.0,
                                                                              'Integer': 1.0,
                                                                              'String': 0.0},
                                                   'default_value': None,
                                                   'description': 'primary key',
                                                   'labels': [],
                                                   'name': 'OWN_PRIMARY',
                                                   'reviewed': None,
                                                   'table': 'secondary_table',
                                                   'value_distribution': None,
                                                   'variable_type': 'PrimaryKey'},
                                   'PRIMARY': {'artifacts': None,
                                               'binning': {'exclude_from_binning': None,
                                                           'ref_high': None,
                                                           'ref_low': None,
                                                           'should_bin': False},
                                               'data_type': 'Integer',
                                               'data_type_distribution': {'Decimal': 0.0,
                                                                          'Integer': 1.0,
                                                                          'String': 0.0},
                                               'default_value': None,
                                               'description': 'is foreign key',
                                               'labels': [],
                                               'name': 'PRIMARY',
                                               'reviewed': None,
                                               'table': 'secondary_table',
                                               'value_distribution': None,
                                               'variable_type': 'ForeignKey'}}}}
        assert actual == expected

    m_handler_dict = MetaDataGenerator(csv_data)

    m_handler_dict.gather_meta_data()
    result_from_dict = m_handler_dict.result
    for table, var_desc_dict in descriptions.items():
        for var, desc in var_desc_dict.items():
            result_from_dict.get_variable(table, var).description = desc
    assert vanilla_dict == result_from_dict.to_dict()


if __name__ == '__main__':
    pytest.main()
