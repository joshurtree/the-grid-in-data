import pandas as pd
import plotly.graph_objects as go

from .chartset import Chart, LineTrace, ChartBuilder
from constants import ALT_CAPACITY_FACTORS, CAPACITY_FACTORS, DATE_FIELD, FREQ_GROUPS
from  datasources.supply import capacity_factors_source, capacity_factors_dataset

def create_capacity_factor_chart():
    """
    Create a chart showing capacity factors by fuel type over time.
    """
    builder = ChartBuilder(
        capacity_factors_source,
        [],
        title='Capacity Factors by Fuel Type', 
        description='This chart shows the capacity factors for different fuel types over time, indicating how efficiently each generation technology is utilized.'
    )

    return builder.create_chart(
        x=DATE_FIELD,
        y=[LineTrace(fuel_type) for fuel_type in CAPACITY_FACTORS],
        y_title='Capacity Factor (%)'
    )

def create_capacity_factor_chart_by_window(window):
    """
    Create a chart showing capacity factors by fuel type over time for a specific window (D, W, M).
    """
    def window_filter(df):
        for fuel_type in ALT_CAPACITY_FACTORS:
            df[f'{fuel_type}'] = df[f'{fuel_type} Capacity Factor ({window})']

        return df[[DATE_FIELD] + ALT_CAPACITY_FACTORS]
    chart_builder = ChartBuilder(capacity_factors_dataset, filter_functions=[window_filter], title=f'Capacity Factors by Fuel Type ({window})', description=f'This chart shows the capacity factors for different fuel types over time for the {window} window, indicating how efficiently each generation technology is utilized.')

    
    return chart_builder.create_chart(
        x=DATE_FIELD,
        y=[LineTrace(fuel_type) for fuel_type in ALT_CAPACITY_FACTORS],
        y_title='Capacity Factor (%)'
    )

def create_capacity_factor_percentiles_chart(window):
    """
    Create a chart showing the number of days in each capacity factor percentile for wind and solar for a specific window (D, W, M).
    """
    def create_dataframe(capacity_df):
        total_years = capacity_df.count()[DATE_FIELD]/365
        calc_field = lambda x, f: capacity_df.loc[(capacity_df[f'{f} Capacity Factor ({window})'] >= x) & (capacity_df[f'{f} Capacity Factor ({window})'] < x+1)].count()[DATE_FIELD] / total_years
        generation_typs = ALT_CAPACITY_FACTORS
        df = []
        for x in range(1, capacity_df[f'Wind Capacity Factor ({window})'].max().astype(int) + 1):
            for fuel_type in generation_typs:
                row = {}
                row["Capacity Factor Percentile"] = x
                row[fuel_type] = calc_field(x, fuel_type)
                df.append(row)
        
        return pd.DataFrame(df)

    builder = ChartBuilder(
        capacity_factors_dataset,
        [
            lambda df: df.resample(FREQ_GROUPS[window], on=DATE_FIELD).first().reset_index(),
            create_dataframe
        ],
        title=f'Capacity Factor Percentiles by Fuel Type ({window})',
        description=f'This chart shows the capacity factor percentiles for different fuel types over time for the {window} window, indicating how efficiently each generation technology is utilized.'
    )
    
    window_label = {'Daily': 'Days', 'Weekly': 'Weeks', 'Monthly': 'Months', 'Quarterly': 'Quarters'}

    chart = builder.create_chart(
        x='Capacity Factor Percentile',
        y=[LineTrace(fuel_type, hover_template=lambda xf,yf,x,y : f"Average {window} Duration: {y}<br>Capacity Factor: {x}<extra></extra>") for fuel_type in ALT_CAPACITY_FACTORS],
        y_title=f'Average Number of {window_label[window]} per Year'
    )
    print(chart.table.head())
    return chart

