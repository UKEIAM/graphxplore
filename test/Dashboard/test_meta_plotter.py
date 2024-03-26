import pytest
from graphxplore.Dashboard import MetadataDistributionPlotter
from graphxplore.MetaDataHandling import (VariableInfo, DataType, VariableType, CategoricalDistribution,
                                          MetricDistribution)

def test_exceptions():
    var_info = VariableInfo('variable', 'table', ['label'], VariableType.Categorical, DataType.String)
    with pytest.raises(AttributeError) as exc:
        MetadataDistributionPlotter.plot_value_distribution(var_info)
    assert str(exc.value) == 'Variable info has no value distribution'
    var_info.value_distribution = 'invalid'
    with pytest.raises(NotImplementedError) as exc:
        MetadataDistributionPlotter.plot_value_distribution(var_info)
    assert str(exc.value) == 'Distribution not implemented'
    with pytest.raises(AttributeError) as exc:
        MetadataDistributionPlotter.plot_data_type_distribution(var_info)
    assert str(exc.value) == 'Variable info has no data type distribution'


def test_fig_generation():
    categorical_info = VariableInfo('variable', 'table', ['label'], VariableType.Categorical, DataType.String)
    categorical_info.value_distribution = CategoricalDistribution(
        category_counts= {'first' : 1, 'second' : 3}, other_count=5, missing_count=0, artifact_count=0)
    MetadataDistributionPlotter.plot_value_distribution(categorical_info)
    categorical_info.data_type_distribution = {DataType.String : 1.0, DataType.Integer : 0.0, DataType.Decimal : 0.0}
    MetadataDistributionPlotter.plot_data_type_distribution(categorical_info)
    metric_info = VariableInfo('variable', 'table', ['label'], VariableType.Metric, DataType.Integer)
    # with outliers
    metric_info.value_distribution = MetricDistribution(
        median=3.5, q1=1.0, q3=6.0,lower_fence=0.0,upper_fence=10.0, outliers=[-1, 13], missing_count=0, artifact_count=5)
    MetadataDistributionPlotter.plot_value_distribution(metric_info)
    # without outliers
    metric_info.value_distribution = MetricDistribution(
        median=3.5, q1=1.0, q3=6.0, lower_fence=0.0, upper_fence=10.0, outliers=[], missing_count=0,
        artifact_count=5)
    MetadataDistributionPlotter.plot_value_distribution(metric_info)