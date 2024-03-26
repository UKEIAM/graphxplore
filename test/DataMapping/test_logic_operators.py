import pytest
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.MetaDataHandling import DataType
from graphxplore.DataMapping.Conditionals import (LogicOperatorParser, AndOperator, OrOperator, MetricOperator,
                                                  MetricOperatorType, StringOperator, StringOperatorType,
                                                  InListOperator, NegatedOperator, AlwaysTrueOperator,
                                                  AggregatorOperator)
from graphxplore.DataMapping import AggregatorType, SourceDataLine

def test_operators():
    # always true
    always_true = AlwaysTrueOperator()
    control_str = '(TRUE)'
    assert str(always_true) == control_str
    actual_operator = LogicOperatorParser.from_string(control_str)
    assert isinstance(actual_operator, AlwaysTrueOperator)
    assert actual_operator.get_required_data() == {}

    # string
    expected_operator = StringOperator('table', 'var', 'val', StringOperatorType.Equals)
    control_str = '(VARIABLE var OF TYPE String IN TABLE table IS "val")'
    assert str(expected_operator) == control_str
    expected_operator.compare = StringOperatorType.Contains
    control_str = '(VARIABLE var OF TYPE String IN TABLE table CONTAINS "val")'
    assert str(expected_operator) == control_str
    actual_operator = LogicOperatorParser.from_string(control_str)
    assert isinstance(actual_operator, StringOperator)
    assert str(actual_operator) == control_str
    assert actual_operator.get_required_data() == {'table' : [('var', None)]}

    # metric
    expected_operator = MetricOperator('table', 'var', 1.5, DataType.Decimal, MetricOperatorType.Equals)
    control_str = '(VARIABLE var OF TYPE Decimal IN TABLE table == 1.5)'
    assert str(expected_operator) == control_str
    expected_operator.compare = MetricOperatorType.SmallerOrEqual
    control_str = '(VARIABLE var OF TYPE Decimal IN TABLE table <= 1.5)'
    assert str(expected_operator) == control_str
    actual_operator = LogicOperatorParser.from_string(control_str)
    assert isinstance(actual_operator, MetricOperator)
    assert str(actual_operator) == control_str
    assert actual_operator.get_required_data() == {'table': [('var', None)]}

    # list
    expected_operator = InListOperator('table', 'var', DataType.String, ['okay', 'alsoOk'])
    control_str = '(VARIABLE var OF TYPE String IN TABLE table IN [okay, alsoOk])'
    assert str(expected_operator) == control_str
    expected_operator = InListOperator('table', 'var', DataType.Integer, [3, 'weird but valid'])
    control_str = '(VARIABLE var OF TYPE Integer IN TABLE table IN [3, "weird but valid"])'
    assert str(expected_operator) == control_str
    actual_operator = LogicOperatorParser.from_string(control_str)
    assert isinstance(actual_operator, InListOperator)
    assert str(actual_operator) == control_str
    assert actual_operator.get_required_data() == {'table': [('var', None)]}

    # negated
    expected_operator = NegatedOperator(expected_operator)
    control_str = '(NOT (VARIABLE var OF TYPE Integer IN TABLE table IN [3, "weird but valid"]))'
    assert str(expected_operator) == control_str
    actual_operator = LogicOperatorParser.from_string(control_str)
    assert isinstance(actual_operator, NegatedOperator)
    assert str(actual_operator) == control_str
    assert actual_operator.get_required_data() == {'table': [('var', None)]}

    # and
    control_str = ('((TRUE) AND (VARIABLE var OF TYPE String IN TABLE table1 IS "val") '
                   'AND (VARIABLE var OF TYPE Integer IN TABLE table2 < 42))')
    actual_operator = LogicOperatorParser.from_string(control_str)
    assert isinstance(actual_operator, AndOperator)
    assert str(actual_operator) == control_str
    assert actual_operator.get_required_data() == {'table1': [('var', None)], 'table2': [('var', None)]}

    # or
    control_str = ('((TRUE) OR (VARIABLE var OF TYPE String IN TABLE table1 IS "val") '
                   'OR (VARIABLE var OF TYPE Integer IN TABLE table2 < 42))')
    actual_operator = LogicOperatorParser.from_string(control_str)
    assert isinstance(actual_operator, OrOperator)
    assert str(actual_operator) == control_str
    assert actual_operator.get_required_data() == {'table1': [('var', None)], 'table2': [('var', None)]}

    # complicated
    negated_one = LogicOperatorParser.from_string('(NOT (VARIABLE var1 OF TYPE Integer IN TABLE table1 '
                                                   'IN [3, weirdButValid]))')
    little_complicated = LogicOperatorParser.from_string('((TRUE) AND (NOT ((TRUE) OR '
                                                          '(VARIABLE var OF TYPE String IN TABLE table IS "val"))))')
    assert isinstance(little_complicated, AndOperator)
    or_one = LogicOperatorParser.from_string('((VARIABLE var2 OF TYPE String IN TABLE table2 IS "val") '
                                              'OR (VARIABLE var3 OF TYPE Integer IN TABLE table3 < 42))')
    more_complicated = AndOperator([negated_one, little_complicated, or_one])
    control_str = ('((NOT (VARIABLE var1 OF TYPE Integer IN TABLE table1 IN [3, weirdButValid])) '
                   'AND ((TRUE) AND (NOT ((TRUE) OR (VARIABLE var OF TYPE String IN TABLE table IS "val")))) '
                   'AND ((VARIABLE var2 OF TYPE String IN TABLE table2 IS "val") '
                   'OR (VARIABLE var3 OF TYPE Integer IN TABLE table3 < 42)))')
    assert str(more_complicated) == control_str
    assert more_complicated.get_required_data() == {'table1': [('var1', None)], 'table2': [('var2', None)],
                                                    'table3': [('var3', None)], 'table': [('var', None)]}

def test_exceptions():
    input_str = 'invalid'
    with pytest.raises(AttributeError) as exc:
        LogicOperatorParser.from_string(input_str)
    assert str(exc.value) == ('Logic sub operator string must start with opening parenthesis: invalid, total string '
                              'was: invalid')
    input_str = '(invalid)'
    with pytest.raises(AttributeError) as exc:
        LogicOperatorParser.from_string(input_str)
    assert str(exc.value) == 'Logic atomic operator string is invalid: (invalid), total string was: (invalid)'
    input_str = '((TRUE) AND (TRUE) OR (TRUE))'
    with pytest.raises(AttributeError) as exc:
        LogicOperatorParser.from_string(input_str)
    assert str(exc.value) == ('Logic sub composite operator string cannot have "AND" and "OR" as composition: '
                              '(TRUE) AND (TRUE) OR (TRUE), total string was: ((TRUE) AND (TRUE) OR (TRUE))')

    operator = StringOperator('table', 'var', 'val', StringOperatorType.Equals)
    source_data = SourceDataLine({'other_table' : {'var' : 'val'}})
    with pytest.raises(AttributeError) as exc:
        operator.valid(source_data)
    assert str(exc.value) == 'Table "table" not found in source data'
    source_data = SourceDataLine({'table': {'other_var': 'val'}})
    with pytest.raises(AttributeError) as exc:
        operator.valid(source_data)
    assert str(exc.value) == 'Variable "var" for table "table" not found in source data'

def test_aggregator_operator():
    operator = AggregatorOperator('table1', 'var1', 42, DataType.String, AggregatorType.Count,
                                  MetricOperatorType.LargerOrEqual)
    expected = '(AGGREGATE COUNT VARIABLE var1 OF TYPE String IN TABLE table1 >= 42)'
    assert str(operator) == expected
    operator = LogicOperatorParser.from_string(expected)
    assert str(operator) == expected
    operator = AggregatorOperator('table2', 'var2', 0, DataType.Decimal, AggregatorType.Min,
                                  MetricOperatorType.Smaller)
    expected = '(AGGREGATE MIN VARIABLE var2 OF TYPE Decimal IN TABLE table2 < 0)'
    assert str(operator) == expected
    operator = LogicOperatorParser.from_string(expected)
    assert str(operator) == expected
    and_input = ('((AGGREGATE COUNT VARIABLE var1 OF TYPE String IN TABLE table1 >= 42)'
                 ' AND (AGGREGATE MIN VARIABLE var2 OF TYPE Decimal IN TABLE table2 < 0))')
    operator = LogicOperatorParser.from_string(and_input)
    assert isinstance(operator, AndOperator)
    assert isinstance(operator.sub_operators[0], AggregatorOperator)
    assert isinstance(operator.sub_operators[1], AggregatorOperator)
    assert str(operator) == and_input
    with pytest.raises(AttributeError) as exc:
        AggregatorOperator('table', 'var', 42, DataType.String, AggregatorType.Min,
                            MetricOperatorType.LargerOrEqual)
    assert str(exc.value) == ('The aggregator type "MIN" is invalid for string value aggregation of '
                              'variable "var" of table "table". Possible aggregator types are: '
                              '"CONCATENATE", "COUNT", "LIST"')

    with pytest.raises(AttributeError) as exc:
        AggregatorOperator('table', 'var', 42, DataType.String, AggregatorType.Concatenate,
                            MetricOperatorType.LargerOrEqual)
    assert str(exc.value) == ('Aggregator type "CONCATENATE" of variable "var" in table "table" must be '
                              'combined with a string operator type. Possible types are: "IS", "CONTAINS"')

    with pytest.raises(AttributeError) as exc:
        AggregatorOperator('table', 'var', 42, DataType.String, AggregatorType.Concatenate,
                           StringOperatorType.Contains)
    assert str(exc.value) == ('Variable "var" in table "table" has mismatch of operator type "CONTAINS" and '
                              'value type to compare with int')

    with pytest.raises(AttributeError) as exc:
        AggregatorOperator('table', 'var', 'invalid', DataType.Decimal, AggregatorType.Min,
                           StringOperatorType.Contains)
    assert str(exc.value) == ('Aggregator type "MIN" of variable "var" in table "table" can only be '
                              'combined with a metric operator type. Possible types are: "==", "<", ">", '
                              '"<=", ">="')

    with pytest.raises(AttributeError) as exc:
        AggregatorOperator('table', 'var', 'invalid', DataType.Decimal, AggregatorType.Min,
                           MetricOperatorType.Equals)
    assert str(exc.value) == ('Variable "var" in table "table" has mismatch of operator type "==" and value '
                              'type to compare with str')

    input_with_whitespace = ('(AGGREGATE CONCATENATE VARIABLE var1 OF TYPE String IN TABLE table1 CONTAINS '
                             '"text with whitespace")')
    operator = LogicOperatorParser.from_string(input_with_whitespace)
    assert isinstance(operator, AggregatorOperator)
    assert operator.value == 'text with whitespace'
    assert str(operator) == input_with_whitespace
    operator = AggregatorOperator('table', 'var', 13.8, DataType.Decimal, AggregatorType.Amplitude,
                                  MetricOperatorType.Smaller)
    expected = '(AGGREGATE AMPLITUDE VARIABLE var OF TYPE Decimal IN TABLE table < 13.8)'
    assert str(operator) == expected
    with pytest.raises(AttributeError) as exc:
        AggregatorOperator('table', 'var', 13.8, DataType.String, AggregatorType.Amplitude, MetricOperatorType.Smaller)
    assert str(exc.value) == ('The aggregator type "AMPLITUDE" is invalid for string value aggregation of variable '
                              '"var" of table "table". Possible aggregator types are: "CONCATENATE", "COUNT", "LIST"')

if __name__ == '__main__':
    pytest.main()