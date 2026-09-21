from dataclasses import dataclass
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from constants import FREQ_GROUPS
from  datasources.supply import monthly_gas_prices_dataset, gas_storage_dataset
import numpy as np
from .chartset import Chart

def filter_and_group_data(data: pd.DataFrame, start_date: datetime, end_date: datetime, period_group: str = 'Daily', gas_usage=[0, 100]):
    #print(f'{len(data)} records before filtering')
    filtered_data = data.copy()

    filtered_data = filtered_data[filtered_data['Date'] >= pd.to_datetime(start_date)]
    filtered_data = filtered_data[filtered_data['Date'] <= pd.to_datetime(end_date)]
    #filtered_data = filtered_data[(filtered_data['GAS_perc'] >= gas_usage[0]) & (filtered_data['GAS_perc'] <= gas_usage[1])]

    if period_group in FREQ_GROUPS:
        freq = FREQ_GROUPS[period_group]
        filtered_data = filtered_data.set_index('Date').resample(freq).mean().reset_index()
        #print(f'{len(filtered_data)} records after resampling to {period_group} frequency')

    return filtered_data


def create_price_chart(start_date=None, end_date=None, period_group='Monthly', gas_usage=[0, 100]) -> Chart:
    data = monthly_gas_prices_dataset.load_data()
    filtered_data = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]
    chart_figure = go.Figure()
    chart_figure.add_trace(go.Scatter(
        x=filtered_data['Date'],
        y=filtered_data['Price'],
        mode='lines',
        name='Gas Price',
        line=dict(color='orange'),
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Gas Price: £{p:.2f}/MWh" for d, p in zip(filtered_data['Date'], filtered_data['Price'])],
        hovertemplate='%{text}<extra></extra>'
    ))
    # Create error bars for forecasted data
    chart_figure.add_trace(go.Scatter(
        x=pd.concat([filtered_data['Date'], filtered_data['Date'][::-1]]),
        y=pd.concat([filtered_data['Min'], filtered_data['Max'][::-1]]),
        fill='toself',
        fillcolor='rgba(255,165,0,0.5)',
        line=dict(color='rgba(255,255,255,0)'),
        mode='lines',
        showlegend=False
    ))
    chart_figure.update_layout(
        title='Monthly Wholesale Gas Price',
        xaxis_title='Date',
        yaxis_title='Price',
        hovermode='closest',
        template='plotly_dark',
        height=600
    )

    return Chart(monthly_gas_prices_dataset, 
                 chart_figure, 
                 title="Monthly Wholesale Gas Price", 
                 description="This chart shows the monthly wholesale gas prices over time.")

def create_storage_chart(start_date=None, end_date=None, period_group='Monthly', gas_usage=[0, 100]) -> Chart:
    data = gas_storage_dataset.load_data()
    filtered_data = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]
    chart_figure = go.Figure()
    chart_figure.add_trace(go.Scatter(
        x=filtered_data['Date'],
        y=filtered_data['Gas Reserves (Days)'],
        mode='lines',
        name='Gas Reserves (Days)',
        line=dict(color='green'),
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Gas Reserves: {r:.2f} Days" for d, r in zip(filtered_data['Date'], filtered_data['Gas Reserves (Days)'])],
        hovertemplate='%{text}<extra></extra>'
    ))
    chart_figure.add_trace(go.Scatter(
        x=filtered_data['Date'],
        y=filtered_data['Gas Capacity (Days)'],
        mode='lines',
        name='Gas Capacity (Days)',
        line=dict(color='blue'),
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Gas Capacity: {c:.2f} Days" for d, c in zip(filtered_data['Date'], filtered_data['Gas Capacity (Days)'])],
        hovertemplate='%{text}<extra></extra>'
    ))
    chart_figure.update_layout(
        title='Gas Reserves (Days)',
        xaxis_title='Date',
        yaxis_title='Gas Reserves (Days)',
        hovermode='closest',
        template='plotly_dark',
        height=600
    )

    return Chart(gas_storage_dataset, 
                 chart_figure, 
                 title="Gas Reserves (Days)", 
                 description="This chart shows the estimated number of days of gas reserves remaining based on current storage and demand.")