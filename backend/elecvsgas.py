from dataclasses import dataclass
from datetime import datetime, date
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backend.constants import FREQ_GROUPS, PROCESSED_DATA_PATH, RAW_DATA_PATH
from datasources.system import gasvselec_dataset
from datasources.gas import daily_gas_prices_dataset, monthly_gas_prices_dataset
import numpy as np
from backend.chartset import Chart

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

def create_chart(start_date, end_date, period_group='Daily', gas_usage=[0, 100], as_ratio=False) -> Chart:
    filtered_data = filter_and_group_data(gasvselec_dataset.load_data(),start_date, end_date, period_group, gas_usage)
    # Create Plotly line chart with gas and electricity prices, and add hover text for each point
    chart_figure =  make_subplots(specs=[[{"secondary_y": True}]])

    if as_ratio:
        filtered_data['Ratio'] = filtered_data['Electricity Price'] / filtered_data['Gas Price']
        chart_figure.add_trace(go.Scatter(
            x=filtered_data['Date'],
            y=filtered_data['Ratio'],
            mode='lines+markers',
            name='Electricity/Gas Price Ratio',
            line=dict(color='green'),
            text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Ratio: {r:.2f}" for d, r in zip(filtered_data['Date'], filtered_data['Ratio'])],
            hovertemplate='%{text}<extra></extra>'
        ), secondary_y=False)
        chart_figure.update_layout(
            title='Electricity Price / Gas Price Ratio vs Date',
            xaxis_title='Date',
            yaxis_title='Ratio',
            hovermode='closest',
            template='plotly_dark',
            height=600
        )
    else:
        chart_figure.add_trace(go.Scatter(
            x=filtered_data['Date'],
            y=filtered_data['Electricity Price'],
            mode='lines+markers',
            name='Electricity Price',
            line=dict(color='blue'),
            text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Electricity Price: £{p:.2f}/MWh" for d, p in zip(filtered_data['Date'], filtered_data['Electricity Price'])],
            hovertemplate='%{text}<extra></extra>',
        ))

        chart_figure.add_trace(go.Scatter(
            x=filtered_data['Date'],
            y=filtered_data['Gas Price'],
            mode='lines+markers',
            name='Gas Price',
            line=dict(color='orange'),
            text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Gas Price: £{p:.2f}/MWh" for d, p in zip(filtered_data['Date'], filtered_data['Gas Price'])],
            hovertemplate='%{text}<extra></extra>',
        ), secondary_y=True)

        chart_figure.update_layout(
            title='Wholesale Price vs Date',
            hovermode='closest',
            template='plotly_dark',
            height=600
        )

        chart_figure.update_xaxes(title_text="Date")
        chart_figure.update_yaxes(title_text="Electricity Price (£/MWh)", secondary_y=False)
        chart_figure.update_yaxes(title_text="Gas Price (£/MWh)", secondary_y=True)

    return Chart(monthly_gas_prices_dataset, chart_figure, title="Wholesale Price vs Date", description="This chart shows the relationship between wholesale electricity and gas prices over time.")

def create_price_chart(start_date=None, end_date=None, period_group='Monthly', gas_usage=[0, 100]) -> Chart:
    data = monthly_gas_prices_dataset.load_data()
    filtered_data = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]
    chart_figure = go.Figure()
    chart_figure.add_trace(go.Scatter(
        x=filtered_data['Date'],
        y=filtered_data['Price'],
        mode='lines+markers',
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

    return Chart(monthly_gas_prices_dataset, chart_figure, title="Monthly Wholesale Gas Price", description="This chart shows the monthly wholesale gas prices over time.")