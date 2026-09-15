import pandas as pd
import plotly.graph_objects as go

from backend.chartset import Chart
from backend.constants import DATE_FIELD
from datasources.system import capacity_factors_source

def create_capacity_factor_chart():
    """
    Create a chart showing capacity factors by fuel type over time.
    """
    # Load data
    capacity_df = capacity_factors_source.load_data()

    fig = go.Figure()
    generation_typs = ['Onshore Wind', 'Offshore Wind', 'Solar']
    for fuel_type in generation_typs:
        fig.add_trace(go.Scatter(
            x=capacity_df[DATE_FIELD],
            y=capacity_df[fuel_type + ' Capacity Factor (%)'],
            name=fuel_type
        ))
    
    return Chart(capacity_factors_source, fig, title='Capacity Factors by Fuel Type', description='This chart shows the capacity factors for different fuel types over time, indicating how efficiently each generation technology is utilized.')