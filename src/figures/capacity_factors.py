import pandas as pd
import plotly.graph_objects as go

from .chartset import Chart, LineTrace, create_chart
from constants import DATE_FIELD, FREQ_GROUPS
from  datasources.supply import capacity_factors_source, capacity_factors_dataset

def create_capacity_factor_chart():
    """
    Create a chart showing capacity factors by fuel type over time.
    """
    return Chart(
        capacity_factors_source, 
        capacity_factors_dataset.load_data(),
        create_chart(
            capacity_factors_source.load_data(),
            x=DATE_FIELD,
            y=[LineTrace(fuel_type + ' Capacity Factor (%)') for fuel_type in ['Onshore Wind', 'Offshore Wind', 'Solar']]
        ),
        title='Capacity Factors by Fuel Type', 
        description='This chart shows the capacity factors for different fuel types over time, indicating how efficiently each generation technology is utilized.',
        
    )

def create_capacity_factor_chart_by_window(window):
    """
    Create a chart showing capacity factors by fuel type over time for a specific window (D, W, M).
    """
    df = capacity_factors_dataset.load_data()
    for fuel_type in ['Wind', 'Solar']:
        df[f'{fuel_type}'] = df[f'{fuel_type} Capacity Factor ({window})']
    
    return Chart(
        capacity_factors_dataset,
        df,
        create_chart(
            df,
            x=DATE_FIELD,
            y=[LineTrace(fuel_type) for fuel_type in ['Wind', 'Solar']],
            y_title='Capacity Factor (%)'
        ),
        title=f'Capacity Factors by Fuel Type ({window})', 
        description=f'This chart shows the capacity factors for different fuel types over time for the {window} window, indicating how efficiently each generation technology is utilized.',
    )

def create_capacity_factor_percentiles_chart(window):
    """
    Create a chart showing the number of days in each capacity factor percentile for wind and solar for a specific window (D, W, M).
    """
    # Load data
    capacity_df = capacity_factors_dataset.load_data()
    total_years = capacity_df.count()[DATE_FIELD]/365
    capacity_df = capacity_df.resample(FREQ_GROUPS[window], on=DATE_FIELD).first().reset_index()
    calc_field = lambda x, f: capacity_df.loc[(capacity_df[f'{f} Capacity Factor ({window})'] >= x) & (capacity_df[f'{f} Capacity Factor ({window})'] < x+1)].count()[DATE_FIELD] / total_years

    fig = go.Figure()
    generation_typs = ['Wind', 'Solar']
    for fuel_type in generation_typs:
        df = []
        for x in range(1, capacity_df[f'{fuel_type} Capacity Factor ({window})'].max().astype(int) + 1):
            row = {}
            row["Capacity Factor Percentile"] = x
            row[f'Duration ({window})'] = calc_field(x, fuel_type)
            df.append(row)
        df = pd.DataFrame(df)

        fig.add_trace(go.Scatter(
            x=df['Capacity Factor Percentile'],
            y=df[f'Duration ({window})'],
            name=fuel_type,
            hovertemplate="Average " + window + " Duration: %{y}<br>Capacity Factor: %{x}<extra></extra>",
        ))
    window_label = {'Daily': 'Days', 'Weekly': 'Weeks', 'Monthly': 'Months', 'Quarterly': 'Quarters'}
    fig.update_layout(
        xaxis_title='Capacity Factor (%)',
        yaxis_title=f'Average Number of {window_label[window]} per Year',
    )

    return Chart(
        capacity_factors_dataset, 
        df,
        fig,
        title=f'Capacity Factor Percentiles by Fuel Type ({window})', 
        description=f'''
        This chart shows the capacity factor percentiles for different fuel types over time for the {window} window, 
        indicating how efficiently each generation technology is utilized.
        '''
    )

