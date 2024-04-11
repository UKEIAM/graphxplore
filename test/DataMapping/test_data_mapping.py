import copy
import pytest
import os
import csv
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.MetaDataHandling import MetaData, VariableType, DataType
from graphxplore.DataMapping import VariableMapping, DataTransformation, DataMapping, MappingCase, SourceDataType, AggregatorType, TableMapping, TableMappingType
from graphxplore.DataMapping.Conclusions import FixedReturnConclusion, CopyConclusion, AggregateConclusion
from graphxplore.DataMapping.Conditionals import (AndOperator, OrOperator, NegatedOperator, StringOperator,
                                                  MetricOperator, AlwaysTrueOperator, StringOperatorType,
                                                  InListOperator, MetricOperatorType, AggregatorOperator)

BASE_PATH = os.path.dirname(__file__)

SOURCE_DIR = os.path.join(BASE_PATH, 'test_data')
SOURCE_META_PATH = os.path.join(BASE_PATH, 'test_data', 'source_meta.json')
FIRST_TARGET_META_PATH = os.path.join(BASE_PATH, 'test_data', 'first_target_meta.json')
FIRST_MAPPING_PATH = os.path.join(BASE_PATH, 'test_output', 'first_mapping.json')
FIRST_OUT_DIR = os.path.join(BASE_PATH, 'test_output', 'first_data_dir')
SECOND_TARGET_META_PATH = os.path.join(BASE_PATH, 'test_data', 'second_target_meta.json')
SECOND_MAPPING_PATH = os.path.join(BASE_PATH, 'test_output', 'second_mapping.json')
SECOND_OUT_DIR = os.path.join(BASE_PATH, 'test_output', 'second_data_dir')
THIRD_MAPPING_PATH = os.path.join(BASE_PATH, 'test_output', 'third_mapping.json')
THIRD_OUT_DIR = os.path.join(BASE_PATH, 'test_output', 'third_data_dir')
FOURTH_MAPPING_PATH = os.path.join(BASE_PATH, 'test_output', 'fourth_mapping.json')
FOURTH_OUT_DIR = os.path.join(BASE_PATH, 'test_output', 'fourth_data_dir')

def test_mapping_checks():
    source_meta = MetaData.load_from_json(SOURCE_META_PATH)
    target_meta = MetaData(['root_target_table', 'child_target_table'])
    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta)
    assert str(exc.value) == 'Target table "root_target_table" has no assigned primary key'
    target_meta.add_variable('root_target_table', 'ROOT_PK')
    target_meta.add_variable('root_target_table', 'ROOT_ATTR')
    target_meta.assign_primary_key('root_target_table', 'ROOT_PK')
    target_meta.add_variable('root_target_table', 'CHILD_PK')
    target_meta.add_variable('child_target_table', 'CHILD_PK')
    target_meta.assign_primary_key('child_target_table', 'CHILD_PK')
    target_meta.add_foreign_key('root_target_table', 'child_target_table', 'CHILD_PK')
    mapping = DataMapping(source_meta, target_meta)
    var_mapping = VariableMapping('root_target_table', 'ROOT_PK', [
        MappingCase(conditional=AlwaysTrueOperator(),
                    conclusion=CopyConclusion(DataType.String, 'first_root_table', 'PK_ROOT_1'))
    ])
    with pytest.raises(AttributeError) as exc:
        mapping.assign_variable_mapping(var_mapping)
    assert str(exc.value) == ('You have to specify the table mapping for target table "root_target_table" '
                              'before adding variable mappings')
    inherit_mapping = TableMapping(TableMappingType.Inherited, to_inherit='root_target_table')
    with pytest.raises(AttributeError) as exc:
        mapping.assign_table_mapping('child_target_table', inherit_mapping)
    assert str(exc.value) == ('Target table "child_target_table" was marked for inheriting from table '
                              '"root_target_table", but this table has no assigned table mapping yet')

    with pytest.raises(AttributeError) as exc:
        mapping.assign_table_mapping('root_target_table', TableMapping(TableMappingType.OneToOne, ['invalid']))
    assert str(exc.value) == ('Source table "invalid" was specified in table mapping of target table '
                              '"root_target_table", but does not exist in source metadata')
    mapping.assign_table_mapping('root_target_table', TableMapping(TableMappingType.OneToOne, ['first_child_table']))
    mapping.assign_table_mapping('child_target_table', inherit_mapping)
    with pytest.raises(AttributeError) as exc:
        mapping.assign_variable_mapping(var_mapping)
    assert str(exc.value) == ('"ROOT_PK" is the primary key of target table "root_target_table". Primary '
                              'keys have no own variable mapping. Their mapping behaviour is defined by the '
                              'table mapping')
    var_mapping = VariableMapping('root_target_table', 'ROOT_ATTR', [
        MappingCase(conditional=AlwaysTrueOperator(),
                    conclusion=CopyConclusion(DataType.String, 'first_root_table', 'PK_ROOT_1'))
    ])
    with pytest.raises(AttributeError) as exc:
        mapping.assign_variable_mapping(var_mapping)
    assert str(exc.value) == ('Source table "first_root_table" used for singular value comparison in '
                              'variable mapping of target variable "ROOT_ATTR" in target table '
                              '"root_target_table", but source table data cannot be used for singular value '
                              'comparison with specified table mapping')
    var_mapping = VariableMapping('root_target_table', 'ROOT_ATTR', [
        MappingCase(conditional=AlwaysTrueOperator(),
                    conclusion=CopyConclusion(DataType.String, 'second_child_table', 'ATTR'))
    ])
    with pytest.raises(AttributeError) as exc:
        mapping.assign_variable_mapping(var_mapping)
    assert str(exc.value) == ('Source table "second_child_table" used for singular value comparison in '
                              'variable mapping of target variable "ROOT_ATTR" in target table '
                              '"root_target_table", but source table data cannot be used for singular value '
                              'comparison with specified table mapping')

    var_mapping = VariableMapping('root_target_table', 'ROOT_ATTR', [
        MappingCase(conditional=AlwaysTrueOperator(),
                    conclusion=CopyConclusion(DataType.String, 'third_child_table', 'ATTR'))
    ])
    mapping.assign_variable_mapping(var_mapping)
    table_mappings = mapping.table_mappings
    var_mappings = mapping.variable_mappings
    del var_mappings['root_target_table']['ROOT_ATTR']
    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta, table_mappings, var_mappings)
    assert str(exc.value) == ('Target variable "ROOT_ATTR" of target table "root_target_table" missing in variable '
                              'mappings')
    invalid_mapping = VariableMapping('invalid', 'invalid', [])
    var_mappings['root_target_table']['ROOT_ATTR'] = invalid_mapping
    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta, table_mappings, var_mappings)
    assert str(exc.value) == ('Mismatch in target table "root_target_table" in variable mapping dict and '
                              '"invalid" in variable mapping')
    invalid_mapping.target_table = 'root_target_table'
    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta, table_mappings, var_mappings)
    assert str(exc.value) == ('Mismatch in target variable "ROOT_ATTR" of target table "root_target_table" '
                              'in variable mapping dict and "invalid" in variable mapping')
    var_mappings['root_target_table']['ROOT_ATTR'] = VariableMapping('root_target_table', 'ROOT_ATTR', [])
    DataMapping(source_meta, target_meta, table_mappings, var_mappings)



def test_mapping_full_init():

    source_meta = MetaData.load_from_json(SOURCE_META_PATH)

    target_meta = MetaData(['root_target_table', 'first_child_target_table', 'second_child_target_table'])
    target_meta.assign_label('root_target_table', 'Root')
    target_meta.assign_label('first_child_target_table', 'FirstChild')
    target_meta.assign_label('second_child_target_table', 'SecondChild')

    for table, pk in [('root_target_table', 'Primary'), ('first_child_target_table', 'PKT_CHILD1'),
                      ('second_child_target_table', 'PKT_CHILD2')]:
        var_info = target_meta.add_variable(table, pk)
        var_info.data_type = DataType.Integer
        target_meta.assign_primary_key(table, pk)
        if table != 'root_target_table':
            var_info = target_meta.add_variable('root_target_table', pk)
            var_info.data_type = DataType.Integer
            target_meta.add_foreign_key('root_target_table', table, pk)

    target_meta.add_variable('root_target_table', 'CopyStrAttr')
    var_info = target_meta.add_variable('first_child_target_table', 'FLOAT_ATTR')
    var_info.data_type = DataType.Decimal
    var_info.variable_type = VariableType.Metric
    var_info = target_meta.add_variable('second_child_target_table', 'INT_ATTR')
    var_info.data_type = DataType.Integer

    table_mappings = {
        'root_target_table' : TableMapping(TableMappingType.OneToOne, ['first_root_table']),
        'first_child_target_table' : TableMapping(TableMappingType.OneToOne, ['first_child_table']),
        'second_child_target_table' : TableMapping(TableMappingType.Inherited, to_inherit='root_target_table')
    }
    var_mappings = {
        'root_target_table': {
            'CopyStrAttr' : VariableMapping('root_target_table', 'CopyStrAttr', [
                MappingCase(conditional=StringOperator('second_child_table', 'ATTR', "", StringOperatorType.Equals),
                            conclusion=FixedReturnConclusion(DataType.String, 'wasMissing')),
                MappingCase(conditional=AlwaysTrueOperator(),
                            conclusion=CopyConclusion(DataType.String, 'first_root_table', 'ATTR1'))
            ]),
            'PKT_CHILD1' : VariableMapping('root_target_table', 'PKT_CHILD1', [
                MappingCase(conditional=AlwaysTrueOperator(),
                            conclusion=CopyConclusion(DataType.Integer, 'first_child_table', 'PK_CHILD_1'))
            ])
        },
        'first_child_target_table' : {
            'FLOAT_ATTR': VariableMapping('first_child_target_table', 'FLOAT_ATTR', [
                MappingCase(conditional=AndOperator([
                    NegatedOperator(InListOperator('third_child_table', 'ATTR', DataType.Integer, ['Na'])),
                    MetricOperator('third_child_table', 'ATTR', 100, DataType.Integer, MetricOperatorType.Smaller)
                ]),
                    conclusion=FixedReturnConclusion(DataType.Decimal, -42.0))
            ])
        },
        'second_child_target_table': {
            'INT_ATTR' : VariableMapping('second_child_target_table', 'INT_ATTR', [
                MappingCase(conditional=OrOperator([
                    MetricOperator('first_root_table', 'ATTR2', 20, DataType.Integer,
                                   MetricOperatorType.LargerOrEqual),
                    StringOperator('first_root_table', 'ATTR1', 'Some', StringOperatorType.Contains)
                ]),
                    conclusion=CopyConclusion(DataType.Integer, 'first_root_table', 'ATTR2')),
                MappingCase(conditional=NegatedOperator(StringOperator('second_child_table', 'ATTR', '',
                                                                       StringOperatorType.Equals)),
                            conclusion=FixedReturnConclusion(DataType.Integer, 42))
            ])
        }
    }

    data_mapping = DataMapping(source_meta, target_meta, table_mappings, var_mappings)

    target_meta.store_in_json(FIRST_TARGET_META_PATH)

    data_mapping.to_json(FIRST_MAPPING_PATH)
    reloaded_mapping = DataMapping.from_json(FIRST_MAPPING_PATH, source_meta, target_meta)
    actual = reloaded_mapping.to_dict()
    expected = {
        'first_child_target_table': {
            'table_mapping': {
                'condition': '(TRUE)',
                'source_tables': ['first_child_table'],
                'to_inherit': None,
                'type': 'OneToOne'
            },
           'variable_mappings': {
               'FLOAT_ATTR': {
                   'cases': [
                       {
                           'if': '((NOT (VARIABLE ATTR OF TYPE Integer IN TABLE third_child_table IN [Na])) '
                              'AND (VARIABLE ATTR OF TYPE Integer IN TABLE third_child_table < 100))',
                           'then': 'RETURN -42.0 OF TYPE Decimal'
                       }],
                   'target_table': 'first_child_target_table',
                   'target_variable': 'FLOAT_ATTR'
               }
           }
        },
        'root_target_table': {
            'table_mapping': {
                'condition': '(TRUE)',
                 'source_tables': ['first_root_table'],
                 'to_inherit': None,
                 'type': 'OneToOne'
            },
            'variable_mappings': {
                'CopyStrAttr': {
                    'cases': [
                        {
                            'if': '(VARIABLE ATTR OF TYPE String IN TABLE second_child_table IS "")',
                            'then': 'RETURN wasMissing OF TYPE String'},
                        {
                            'if': '(TRUE)',
                            'then': 'COPY VARIABLE ATTR1 IN TABLE first_root_table IF TYPE IS String'
                        }
                    ],
                    'target_table': 'root_target_table',
                    'target_variable': 'CopyStrAttr'
                },
                'PKT_CHILD1': {
                    'cases': [
                        {
                            'if': '(TRUE)',
                            'then': 'COPY VARIABLE PK_CHILD_1 IN TABLE first_child_table IF TYPE IS Integer'
                        }
                    ],
                    'target_table': 'root_target_table',
                    'target_variable': 'PKT_CHILD1'
                }
            }
        },
        'second_child_target_table': {
            'table_mapping': {
                'condition': '(TRUE)',
                'source_tables': [],
                'to_inherit': 'root_target_table',
                'type': 'Inherited'
            },
            'variable_mappings': {
                'INT_ATTR': {
                    'cases': [
                        {
                            'if': '((VARIABLE ATTR2 OF TYPE Integer IN TABLE first_root_table >= 20) '
                                  'OR (VARIABLE ATTR1 OF TYPE String IN TABLE first_root_table CONTAINS "Some"))',
                            'then': 'COPY VARIABLE ATTR2 IN TABLE first_root_table IF TYPE IS Integer'
                        },
                        {
                            'if': '(NOT (VARIABLE ATTR OF TYPE String IN TABLE second_child_table IS ""))',
                            'then': 'RETURN 42 OF TYPE Integer'}],
                    'target_table': 'second_child_target_table',
                    'target_variable': 'INT_ATTR'
                }
            }
        }
    }
    assert actual == expected

def test_data_creation():
    source_meta = MetaData.load_from_json(SOURCE_META_PATH)
    target_meta = MetaData.load_from_json(FIRST_TARGET_META_PATH)
    mapping = DataMapping.from_json(FIRST_MAPPING_PATH, source_meta, target_meta)
    transformation = DataTransformation(mapping)
    if not os.path.exists(FIRST_OUT_DIR):
        os.mkdir(FIRST_OUT_DIR)
    transformation.transform_to_target(SourceDataType.CSV, SOURCE_DIR, FIRST_OUT_DIR)

    source_data_dict = {}
    for table in source_meta.get_table_names():
        with open(os.path.join(SOURCE_DIR, table + '.csv')) as file:
            reader = csv.DictReader(file)
            source_data_dict[table] = [line for line in reader]
    target_data_dict = {}
    transformation.transform_to_target(SourceDataType.CSV, source_data_dict, target_data_dict)

    with open(os.path.join(FIRST_OUT_DIR, 'root_target_table.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['Primary', 'PKT_CHILD1', 'PKT_CHILD2', 'CopyStrAttr'],
                    ['0', '0', '0', 'wasMissing'],
                    ['1', '1', '1', 'SomeText'],
                    ['2', '0', '0', 'AnotherText']]

        assert actual == expected
        actual_dict_data = [list(target_data_dict['root_target_table'][0].keys())] + [list(line.values()) for line in target_data_dict['root_target_table']]
        assert actual == actual_dict_data

    with open(os.path.join(FIRST_OUT_DIR, 'first_child_target_table.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['PKT_CHILD1', 'FLOAT_ATTR'],
                    ['0', ''],
                    ['1', '-42.0']]

        assert actual == expected
        actual_dict_data = [list(target_data_dict['first_child_target_table'][0].keys())]\
                           + [list(line.values()) for line in target_data_dict['first_child_target_table']]
        assert actual == actual_dict_data

    with open(os.path.join(FIRST_OUT_DIR, 'second_child_target_table.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['PKT_CHILD2', 'INT_ATTR'],
                    ['0', '42'],
                    ['1', '17']]

        assert actual == expected
        actual_dict_data = [list(target_data_dict['second_child_target_table'][0].keys())] \
                           + [list(line.values()) for line in target_data_dict['second_child_target_table']]
        assert actual == actual_dict_data

def test_table_concatenation():
    source_meta = MetaData.load_from_json(SOURCE_META_PATH)

    target_meta = MetaData(['root', 'child'])
    target_meta.assign_label('root', 'Root')
    target_meta.assign_label('child', 'Child')
    var_info = target_meta.add_variable('root', 'NEW_PK')
    var_info.data_type = DataType.Integer
    target_meta.assign_primary_key('root', 'NEW_PK')
    var_info = target_meta.add_variable('root', 'ORIGIN_PK_1')
    var_info.data_type = DataType.Integer
    var_info = target_meta.add_variable('root', 'ORIGIN_PK_2')
    var_info.data_type = DataType.Integer
    var_info = target_meta.add_variable('root', 'PK_CHILD')
    var_info.data_type = DataType.Integer
    var_info = target_meta.add_variable('root', 'ATTR1')
    var_info.data_type = DataType.String
    var_info = target_meta.add_variable('root', 'ATTR2')
    var_info.data_type = DataType.Decimal
    var_info = target_meta.add_variable('child', 'PK_CHILD')
    var_info.data_type = DataType.Integer
    target_meta.assign_primary_key('child', 'PK_CHILD')
    var_info = target_meta.add_variable('child', 'ATTR')
    var_info.data_type = DataType.String
    target_meta.add_foreign_key('root', 'child', 'PK_CHILD')

    target_meta.store_in_json(SECOND_TARGET_META_PATH)

    table_mappings = {
        'root' : TableMapping(TableMappingType.Concatenate, source_tables=['first_root_table', 'second_root_table']),
        'child' : TableMapping(TableMappingType.Inherited, to_inherit='root')
    }

    var_mappings = {
        'root' : {
            'ORIGIN_PK_1': VariableMapping(target_table='root', target_variable='ORIGIN_PK_1', cases=[
                                          MappingCase(AlwaysTrueOperator(),
                                                      CopyConclusion(DataType.Integer, 'first_root_table', 'PK_ROOT_1'))
                                      ]),
            'ORIGIN_PK_2': VariableMapping(target_table='root', target_variable='ORIGIN_PK_2', cases=[
                                               MappingCase(AlwaysTrueOperator(),
                                                           CopyConclusion(DataType.Integer, 'second_root_table',
                                                                          'PK_ROOT_1'))
                                           ]),
            'ATTR1' : VariableMapping(target_table='root', target_variable='ATTR1', cases=[
                                          MappingCase(StringOperator('second_child_table', 'ATTR', 'notMissing',
                                                                     StringOperatorType.Equals),
                                                      FixedReturnConclusion(DataType.String, 'firstCase')),
                                          MappingCase(StringOperator('first_root_table', 'ATTR1', 'Some',
                                                                     StringOperatorType.Contains),
                                                      FixedReturnConclusion(DataType.String, 'secondCase'))
                                      ]),
            'ATTR2' : VariableMapping(target_table='root', target_variable='ATTR2', cases=[
                                          MappingCase(MetricOperator('second_root_table', 'ATTR', 0, DataType.Decimal,
                                                                     MetricOperatorType.Smaller),
                                                      CopyConclusion(DataType.Decimal, 'second_root_table', 'ATTR')),
                                          MappingCase(AlwaysTrueOperator(),
                                                      FixedReturnConclusion(DataType.Decimal, -999.0))
                                      ]),
            # will be deleted
            'PK_CHILD' : VariableMapping(target_table='root', target_variable='PK_CHILD', cases=[
                MappingCase(AlwaysTrueOperator(),
                            FixedReturnConclusion(DataType.String, 'invalid'))
            ])
        },
        'child' : {
            'ATTR' : VariableMapping(target_table='child', target_variable='ATTR', cases=[
                                         MappingCase(MetricOperator('second_root_table', 'ATTR', -3.0, DataType.Decimal,
                                                                    MetricOperatorType.LargerOrEqual),
                                                     FixedReturnConclusion(DataType.String, 'valid')),
                                         MappingCase(AlwaysTrueOperator(),
                                                     FixedReturnConclusion(DataType.String, 'invalid'))
                                     ])
        }
    }

    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta, table_mappings, var_mappings)
    assert str(exc.value) == ('Variable "PK_CHILD" is a foreign key that is used for inheritance of table '
                              'mapping of "root". It should not have a variable mapping')
    del var_mappings['root']['PK_CHILD']
    data_mapping = DataMapping(source_meta, target_meta, table_mappings, var_mappings)
    data_mapping.to_json(SECOND_MAPPING_PATH)
    data_transformation = DataTransformation(data_mapping)

    if not os.path.exists(SECOND_OUT_DIR):
        os.mkdir(SECOND_OUT_DIR)

    data_transformation.transform_to_target(SourceDataType.CSV, SOURCE_DIR, SECOND_OUT_DIR)

    with open(os.path.join(SECOND_OUT_DIR, 'root.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['NEW_PK', 'ORIGIN_PK_1', 'ORIGIN_PK_2', 'PK_CHILD', 'ATTR1', 'ATTR2'],
                     ['0', '0', '', '0', 'secondCase', '-999.0'],
                     ['1', '1', '', '0', 'firstCase', '-999.0'],
                     ['2', '2', '', '0', 'firstCase', '-999.0'],
                     ['3', '', '0', '1', '', '-1.5'],
                     ['4', '', '1', '0', '', '-999.0']]

        assert actual == expected

    with open(os.path.join(SECOND_OUT_DIR, 'child.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['PK_CHILD', 'ATTR'],
                    ['0', 'invalid'],
                    ['1', 'valid']]

        assert actual == expected

def test_key_merging():
    source_meta = MetaData.load_from_json(SOURCE_META_PATH)
    target_meta = MetaData.load_from_json(SECOND_TARGET_META_PATH)

    mapping = DataMapping.from_json(SECOND_MAPPING_PATH, source_meta, target_meta)
    assert not mapping.variable_should_get_mapped('root', 'PK_CHILD')
    with pytest.raises(AttributeError) as exc:
        mapping.get_variable_mapping('root', 'PK_CHILD')
    assert str(exc.value) == ('"PK_CHILD" is a foreign key of target table "root" which is used for '
                              'inheritance of its table mapping. These foreign keys have no own variable '
                              'mapping. Their mapping behaviour is defined by the table mapping')
    mapping.assign_table_mapping('child', TableMapping(TableMappingType.OneToOne, ['first_root_table']))
    assert mapping.variable_should_get_mapped('root', 'PK_CHILD')
    assert mapping.get_variable_mapping('root', 'PK_CHILD').cases == []
    mapping.assign_table_mapping('child', TableMapping(TableMappingType.Inherited, to_inherit='root'))
    assert not mapping.variable_should_get_mapped('root', 'PK_CHILD')
    with pytest.raises(AttributeError) as exc:
        mapping.get_variable_mapping('root', 'PK_CHILD')
    assert str(exc.value) == ('"PK_CHILD" is a foreign key of target table "root" which is used for '
                              'inheritance of its table mapping. These foreign keys have no own variable '
                              'mapping. Their mapping behaviour is defined by the table mapping')

    mapping.assign_table_mapping('root', TableMapping(TableMappingType.Merge, ['first_root_table', 'second_root_table']))
    mapping.to_json(THIRD_MAPPING_PATH)

    data_transformation = DataTransformation(mapping)

    if not os.path.exists(THIRD_OUT_DIR):
        os.mkdir(THIRD_OUT_DIR)

    data_transformation.transform_to_target(SourceDataType.CSV, SOURCE_DIR, THIRD_OUT_DIR)

    with open(os.path.join(THIRD_OUT_DIR, 'root.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['NEW_PK', 'ORIGIN_PK_1', 'ORIGIN_PK_2', 'PK_CHILD', 'ATTR1', 'ATTR2'],
                     ['0', '0', '0', '0', 'secondCase', '-1.5'],
                     ['1', '1', '1', '1', 'firstCase', '-999.0'],
                     ['2', '2', '', '1', 'firstCase', '-999.0']]

        assert actual == expected

    with open(os.path.join(THIRD_OUT_DIR, 'child.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['PK_CHILD', 'ATTR'],
                    ['0', 'valid'],
                    ['1', 'invalid']]

        assert actual == expected

def test_variable_mapping_exceptions():
    case = {
        'if': '(TRUE)',
        'then': 'RETURN 15.0 OF TYPE Decimal'
    }
    input_dict = {
        'target_table' : 'table',
        'target_variable': 'var',
        'cases': [case]
    }

    var_mapping = VariableMapping.from_dict(input_dict)
    assert var_mapping.sources == {}
    assert var_mapping.target_table == 'table'
    assert var_mapping.target_variable == 'var'
    assert var_mapping.cases[0].to_dict() == case

    invalid_case = copy.deepcopy(case)
    invalid_case['if'] = 'invalid'
    invalid_input = copy.deepcopy(input_dict)
    invalid_input['cases'] = [invalid_case]
    with pytest.raises(AttributeError) as exc:
        VariableMapping.from_dict(invalid_input)
    assert str(exc.value) == ('Logic sub operator string must start with opening parenthesis: invalid, '
                              'total string was: invalid')
    invalid_case['if'] = '(TRUE)'
    invalid_case['then'] = 'invalid'
    with pytest.raises(AttributeError) as exc:
        VariableMapping.from_dict(invalid_input)
    assert str(exc.value) == 'The input string invalid is not a valid conclusion'

    invalid_input['target_table'] = []
    with pytest.raises(AttributeError) as exc:
        VariableMapping.from_dict(invalid_input)
    assert str(exc.value) == 'Variable mapping dictionary entry "target_table" must be of type "str"'

    invalid_input['target_table'] = 'table'
    invalid_input['cases'] = [[]]
    with pytest.raises(AttributeError) as exc:
        VariableMapping.from_dict(invalid_input)
    assert str(exc.value) == 'Variable mapping dictionary entry "cases" must be a list of dicts'

def test_mapping_with_aggregation():
    source_meta = MetaData.load_from_json(SOURCE_META_PATH)
    target_meta = MetaData(['root', 'child'])
    target_meta.assign_label('root', 'Root')
    target_meta.assign_label('child', 'Child')
    info = target_meta.add_variable('root', 'ROOT_PK')
    info.data_type = DataType.Integer
    target_meta.assign_primary_key('root', 'ROOT_PK')
    info = target_meta.add_variable('root', 'NON_AGGREGATED_ATTR_CHILD_3')
    info.data_type = DataType.Decimal
    target_meta.add_variable('root', 'CONCATENATED_ATTR1_ROOT_1')
    info = target_meta.add_variable('child', 'CHILD_PK')
    info.data_type = DataType.Integer
    target_meta.assign_primary_key('child', 'CHILD_PK')
    info = target_meta.add_variable('root', 'CHILD_PK')
    info.data_type = DataType.Integer
    target_meta.add_foreign_key('root', 'child', 'CHILD_PK')
    info = target_meta.add_variable('child', 'SUMMED_ATTR_ROOT_2')
    info.data_type = DataType.Decimal
    info = target_meta.add_variable('child', 'AVG_ATTR2_ROOT_1')
    info.data_type = DataType.Decimal

    table_mappings = {
        'root' : TableMapping(TableMappingType.OneToOne, ['first_child_table']),
        'child' : TableMapping(TableMappingType.Inherited, to_inherit='root')
    }

    var_mappings = {
        'root' : {
            'NON_AGGREGATED_ATTR_CHILD_3': VariableMapping(target_table='root',
                                                           target_variable='NON_AGGREGATED_ATTR_CHILD_3', cases=[
                MappingCase(AggregatorOperator('second_root_table', 'ATTR', 'NaN', DataType.String, AggregatorType.List,
                                               StringOperatorType.Contains),
                            CopyConclusion(DataType.String, 'third_child_table', 'ATTR'))
            ]),
            'CONCATENATED_ATTR1_ROOT_1': VariableMapping(target_table='root',
                                                         target_variable='CONCATENATED_ATTR1_ROOT_1', cases=[
                    MappingCase(
                        AlwaysTrueOperator(),
                        AggregateConclusion(DataType.String, 'first_root_table', 'ATTR1', AggregatorType.Concatenate))
                ]),
        },
        'child' : {
            'SUMMED_ATTR_ROOT_2': VariableMapping(target_table='child',
                                                           target_variable='SUMMED_ATTR_ROOT_2', cases=[
                    MappingCase(
                        MetricOperator('first_child_table', 'ATTR', 0.7, DataType.Decimal, MetricOperatorType.Equals),
                        AggregateConclusion(DataType.Decimal, 'second_root_table', 'ATTR', AggregatorType.Sum))
                ]),
            'AVG_ATTR2_ROOT_1': VariableMapping(target_table='child',
                                                         target_variable='AVG_ATTR2_ROOT_1', cases=[
                    MappingCase(
                        AlwaysTrueOperator(),
                        AggregateConclusion(DataType.Decimal, 'first_root_table', 'ATTR2', AggregatorType.Mean))
                ])
        }
    }

    data_mapping = DataMapping(source_meta, target_meta, table_mappings, var_mappings)

    data_transformation = DataTransformation(data_mapping)
    data_mapping.to_json(FOURTH_MAPPING_PATH)
    assert data_mapping.to_dict() == {
        'child': {
            'table_mapping': {
                'condition': '(TRUE)',
                'source_tables': [],
                'to_inherit': 'root',
                'type': 'Inherited'
            },
           'variable_mappings': {
               'AVG_ATTR2_ROOT_1': {
                   'cases': [
                       {
                           'if': '(TRUE)',
                           'then': 'AGGREGATE MEAN VARIABLE ATTR2 OF TYPE Decimal IN TABLE first_root_table'
                       }
                   ],
                   'target_table': 'child',
                   'target_variable': 'AVG_ATTR2_ROOT_1'},
               'SUMMED_ATTR_ROOT_2': {
                   'cases': [
                       {
                           'if': '(VARIABLE ATTR OF TYPE Decimal IN TABLE first_child_table == 0.7)',
                           'then': 'AGGREGATE SUM VARIABLE ATTR OF TYPE Decimal IN TABLE second_root_table'
                       }
                   ],
                   'target_table': 'child',
                   'target_variable': 'SUMMED_ATTR_ROOT_2'
               }
           }
        },
        'root': {
            'table_mapping': {
                'condition': '(TRUE)',
                'source_tables': ['first_child_table'],
                'to_inherit': None,
                'type': 'OneToOne'
            },
            'variable_mappings': {
                'CONCATENATED_ATTR1_ROOT_1': {
                    'cases': [
                        {
                            'if': '(TRUE)',
                            'then': 'AGGREGATE CONCATENATE VARIABLE ATTR1 OF TYPE String IN TABLE first_root_table'
                        }
                    ],
                    'target_table': 'root',
                    'target_variable': 'CONCATENATED_ATTR1_ROOT_1'
                },
                'NON_AGGREGATED_ATTR_CHILD_3': {
                    'cases': [
                        {
                            'if': '(AGGREGATE LIST VARIABLE ATTR OF TYPE String IN TABLE second_root_table CONTAINS '
                                  '"NaN")',
                            'then': 'COPY VARIABLE ATTR IN TABLE third_child_table IF TYPE IS String'}],
                    'target_table': 'root',
                    'target_variable': 'NON_AGGREGATED_ATTR_CHILD_3'
                }
            }
        }
    }

    if not os.path.exists(FOURTH_OUT_DIR):
        os.mkdir(FOURTH_OUT_DIR)

    data_transformation.transform_to_target(SourceDataType.CSV, SOURCE_DIR, FOURTH_OUT_DIR)

    with open(os.path.join(FOURTH_OUT_DIR, 'root.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['ROOT_PK', 'NON_AGGREGATED_ATTR_CHILD_3', 'CONCATENATED_ATTR1_ROOT_1', 'CHILD_PK'],
                     ['0', '', 'AnotherText;SomeText', '0'],
                     ['1', '99', 'SomeText', '1']]

        assert actual == expected

    with open(os.path.join(FOURTH_OUT_DIR, 'child.csv')) as file:
        actual = [line for line in csv.reader(file)]
        expected = [['CHILD_PK', 'SUMMED_ATTR_ROOT_2', 'AVG_ATTR2_ROOT_1'],
                     ['0', '-1.5', '27.5'],
                     ['1', '', '17.0']]

        assert actual == expected

def test_partially_empty_mapping():
    source_meta = MetaData.load_from_json(SOURCE_META_PATH)
    target_meta = MetaData(['first', 'second'])
    target_meta.add_variable('first', 'FIRST_PK')
    target_meta.assign_primary_key('first', 'FIRST_PK')
    target_meta.add_variable('first', 'FIRST_ATTR')
    target_meta.add_variable('second', 'SECOND_PK')
    target_meta.assign_primary_key('second', 'SECOND_PK')
    target_meta.add_variable('second', 'SECOND_ATTR')
    # empty
    mapping = DataMapping(source_meta, target_meta)

    unassigned_table_mapping = TableMapping(type=None, source_tables=[])

    # add unassigned table mapping
    mapping.assign_table_mapping('first', unassigned_table_mapping)

    table_mappings = {
        'first' : unassigned_table_mapping
    }
    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta, table_mappings)
    assert str(exc.value) == 'Target table "second" does not exist in table mapping dict'

    table_mappings = {
        'first': TableMapping(type=None, source_tables=[]),
        'second' : TableMapping(type=None, source_tables=[])
    }
    DataMapping(source_meta, target_meta, table_mappings)

    var_mappings = {
        'first' : {
            'FIRST_ATTR' : VariableMapping('first', 'FIRST_ATTR', [])
        },
        'second' : {
            'SECOND_ATTR': VariableMapping('second', 'SECOND_ATTR', [])
        }
    }

    DataMapping(source_meta, target_meta, table_mappings, var_mappings)

    var_mappings = {
        'first': {
            'FIRST_ATTR': VariableMapping('first', 'FIRST_ATTR', [])
        },
        'second': {}
    }

    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta, table_mappings, var_mappings)
    assert str(exc.value) == 'Target variable "SECOND_ATTR" of target table "second" missing in variable mappings'

    var_mappings = {
        'first': {
            'FIRST_ATTR': VariableMapping('first', 'FIRST_ATTR', [
                MappingCase(conditional=AlwaysTrueOperator(), conclusion=FixedReturnConclusion(DataType.String, 'true'))
            ])
        },
        'second': {
            'SECOND_ATTR': VariableMapping('second', 'SECOND_ATTR', [])
        }
    }

    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta, table_mappings, var_mappings)
    assert str(exc.value) == ('Target variable "FIRST_ATTR" of table "first" already mapped in variable '
                              'mapping dict, but its table is still unmapped')

    with pytest.raises(AttributeError) as exc:
        DataMapping(source_meta, target_meta, variable_mappings=var_mappings)
    assert str(exc.value) == ('Target variable "FIRST_ATTR" of table "first" already mapped in variable '
                              'mapping dict, but its table is still unmapped')

    unassigned_table_mapping_dict = {
        'type' : None,
        'source_tables' : [],
        'to_inherit' : None,
        'condition' : '(TRUE)'
    }

    table_mapping = TableMapping.from_dict(unassigned_table_mapping_dict)
    assert table_mapping.to_dict() == unassigned_table_mapping_dict

if __name__ == '__main__':
    pytest.main()