from dataclasses import dataclass
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from constants import FREQ_GROUPS, PROCESSED_DATA_PATH, RAW_DATA_PATH
from  datasources.system import gasvselec_dataset
from  datasources.supply import daily_gas_prices_dataset, monthly_gas_prices_dataset
import numpy as np
from .chartset import Chart

def filter_and_group_data(data: pd.DataFrame, start_date: datetime, end_date: datetime, period_group: str = 'Daily', target_generation:str="Low Carbon", usage=[0, 100]):
    filtered_data = data.copy()

    filtered_data = filtered_data[filtered_data['Date'] >= pd.to_datetime(start_date)]
    filtered_data = filtered_data[filtered_data['Date'] <= pd.to_datetime(end_date)]
    gapped_data_before = len(filtered_data)
    filtered_data = filtered_data[(filtered_data[f'{target_generation} (%)'] >= usage[0]) & (filtered_data[f'{target_generation} (%)'] <= usage[1])]
    gapped_data_after = len(filtered_data)

    if period_group in FREQ_GROUPS:
        freq = FREQ_GROUPS[period_group]
        filtered_data = filtered_data.set_index('Date').resample(freq).mean().reset_index()

    return filtered_data, gapped_data_before != gapped_data_after

def create_chart(start_date, end_date, period_group='Daily', target_generation:str="Low Carbon", usage=(0, 100), as_ratio=False) -> Chart:
    filtered_data, gapped_data = filter_and_group_data(gasvselec_dataset.load_data(),start_date, end_date, period_group, target_generation, usage)
    # Create Plotly line chart with gas and electricity prices, and add hover text for each point
    chart_figure =  make_subplots(specs=[[{"secondary_y": True}]])
    marker_type = 'markers' if gapped_data else 'lines'

    if as_ratio:
        filtered_data['Ratio'] = filtered_data['Electricity Price'] / filtered_data['Gas Price']
        chart_figure.add_trace(go.Scatter(
            x=filtered_data['Date'],
            y=filtered_data['Ratio'],
            mode=marker_type,
            name='Electricity/Gas Price Ratio',
            line=dict(color='green'),
            text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Ratio: {r:.2f}" for d, r in zip(filtered_data['Date'], filtered_data['Ratio'])],
            hovertemplate='%{text}<extra></extra>'
        ), secondary_y=False)
        chart_figure.update_layout(
            xaxis_title='Date',
            yaxis_title='Ratio',
            hovermode='closest',
        )
    else:
        chart_figure.add_trace(go.Scatter(
            x=filtered_data['Date'],
            y=filtered_data['Electricity Price'],
            mode=marker_type,
            name='Electricity Price',
            line=dict(color='blue'),
            text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Electricity Price: £{p:.2f}/MWh" for d, p in zip(filtered_data['Date'], filtered_data['Electricity Price'])],
            hovertemplate='%{text}<extra></extra>',
        ))

        chart_figure.add_trace(go.Scatter(
            x=filtered_data['Date'],
            y=filtered_data['Gas Price'],
            mode=marker_type,
            name='Gas Price',
            line=dict(color='orange'),
            text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Gas Price: £{p:.2f}/MWh" for d, p in zip(filtered_data['Date'], filtered_data['Gas Price'])],
            hovertemplate='%{text}<extra></extra>',
        ), secondary_y=True)

        chart_figure.update_xaxes(title_text="Date")
        chart_figure.update_yaxes(title_text="Electricity Price (£/MWh)", secondary_y=False)
        chart_figure.update_yaxes(title_text="Gas Price (£/MWh)", secondary_y=True)

    return Chart(gasvselec_dataset, filtered_data, chart_figure, title="Wholesale Price vs Gas Price", description="This chart shows the relationship between wholesale electricity and gas prices over time.")
