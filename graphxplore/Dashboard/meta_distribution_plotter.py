import plotly.graph_objects as go
from graphxplore.MetaDataHandling import VariableInfo, MetricDistribution, CategoricalDistribution

class MetadataDistributionPlotter:

    @staticmethod
    def plot_value_distribution(var_info: VariableInfo) -> go.Figure:
        """Plots the value distribution of a variable. For metric variables, a box plot is generated. For categorical
        variables, a pie plot is generated

        :param var_info: The variable info for the distribution to plot
        :return: Returns the plotted figure which can e.g. be used in streamlit or notebooks
        """
        if var_info.value_distribution is None:
            raise AttributeError('Variable info has no value distribution')
        variable = var_info.name
        if isinstance(var_info.value_distribution, MetricDistribution):
            if len(var_info.value_distribution.outliers) > 0:
                box = go.Box(y=[var_info.value_distribution.outliers], boxpoints='outliers', name=variable)
            else:
                box = go.Box(y=[[0]], boxpoints=False, name=variable)
            fig = go.Figure(data=[box])
            fig.update_traces(q1=[var_info.value_distribution.q1], median=[var_info.value_distribution.median],
                              q3=[var_info.value_distribution.q3],
                              lowerfence=[var_info.value_distribution.lower_fence],
                              upperfence=[var_info.value_distribution.upper_fence],
                              hoverinfo = 'y')
            fig.update_xaxes(showticklabels=False)
        elif isinstance(var_info.value_distribution, CategoricalDistribution):
            fig = go.Figure()
            labels = list(var_info.value_distribution.category_counts.keys())
            values = list(var_info.value_distribution.category_counts.values())
            if var_info.value_distribution.other_count > 0:
                labels.append('Other (concluded by GXP)')
                values.append(var_info.value_distribution.other_count)
            fig.add_trace(go.Pie(labels=labels, values=values, name=variable))
            fig.update_traces(textinfo='label+value')
        else:
            raise NotImplementedError('Distribution not implemented')
        return fig

    @staticmethod
    def plot_data_type_distribution(var_info: VariableInfo) -> go.Figure:
        """Plots the data type distribution of a variable as a pie chart

        :param var_info: The variable info for the distribution to plot
        :return: Returns the plotted figure which can e.g. be used in streamlit or notebooks
                """
        if var_info.data_type_distribution is None:
            raise AttributeError('Variable info has no data type distribution')
        casted_type_dist = {data_type.value: frac for data_type, frac in var_info.data_type_distribution.items()}
        fig = go.Figure()
        fig.add_trace(go.Pie(labels=list(casted_type_dist.keys()),
                                       values=list(casted_type_dist.values())))
        fig.update_traces(textinfo='label+percent', hoverinfo='label+percent')
        fig.update_layout(showlegend=False)
        return fig
