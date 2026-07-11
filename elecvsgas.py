from dataclasses import dataclass
from datetime import datetime, date
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from constants import PERIOD_GROUPS, TRANSFORMED_DATA_DIR, RAW_DATA_DIR
import numpy as np

electricity_prices = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'daily_data.csv')).rename(columns={'Price': 'Electricity Price', 'SettlementDate': 'Date'}).assign(Date=lambda df: pd.to_datetime(df['Date'], format='mixed'))
electricity_prices = electricity_prices.groupby(electricity_prices['Date']).agg({'Electricity Price': 'mean'}).reset_index()
gas_prices = pd.read_csv(os.path.join(RAW_DATA_DIR, 'gas_prices.csv')).rename(columns={'SAP actual day': 'Gas Price'}).assign(Date=lambda df: pd.to_datetime(df['Date'], format='mixed')).set_index('Date')
gas_prices['Gas Price'] = gas_prices['Gas Price']*10
gas_prices.drop(columns=['SAP seven-day rolling average'], inplace=True)
data: pd.DataFrame = pd.merge(electricity_prices, gas_prices, on='Date', how='inner').assign(Ratio=lambda df: df['Electricity Price'] / df['Gas Price'])

def create_trendline(x, y):
    # Fit a linear regression model to the data
    coeffs = np.polyfit(x, y, 1)
    trendline = np.poly1d(coeffs)
    return trendline(x)

def filter_and_group_data(start_date, end_date, period_group='Daily'):
    print(f'{len(data)} records before filtering')
    filtered_data = data.copy()

    filtered_data = filtered_data[filtered_data['Date'] >= pd.to_datetime(start_date)]
    filtered_data = filtered_data[filtered_data['Date'] <= pd.to_datetime(end_date)]
    print(f'{len(filtered_data)} records after date filtering')

    if period_group in PERIOD_GROUPS:
        freq = PERIOD_GROUPS[period_group]
        filtered_data = filtered_data.set_index('Date').resample(freq).mean().reset_index()
        print(f'{len(filtered_data)} records after resampling to {period_group} frequency')

    return filtered_data

def create_chart(start_date, end_date, period_group='Daily'):
    filtered_data = filter_and_group_data(start_date, end_date, period_group)

    # Create Plotly line chart with gas and electricity prices, and add hover text for each point
    chart_figure =  make_subplots(specs=[[{"secondary_y": True}]])
    chart_figure.add_trace(go.Scatter(
        x=filtered_data['Date'],
        y=filtered_data['Electricity Price'],
        mode='lines+markers',
        name='Electricity Price',
        line=dict(color='blue'),
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Electricity Price: £{p:.2f}/MWh" for d, p in zip(filtered_data['Date'], filtered_data['Electricity Price'])],
        hovertemplate='%{text}<extra></extra>',
    ), secondary_y=False)

    # # Add trendline for electricity price
    # trendline_electricity = create_trendline(filtered_data['Date'].map(datetime.toordinal), filtered_data['Electricity Price'])

    # chart_figure.add_trace(go.Scatter(
    #     x=filtered_data['Date'],
    #     y=trendline_electricity,
    #     mode='lines',
    #     name='Electricity Price Trendline',
    #     line=dict(color='green', dash='dash')
    # ), secondary_y=False)

    chart_figure.add_trace(go.Scatter(
        x=filtered_data['Date'],
        y=filtered_data['Gas Price'],
        mode='lines+markers',
        name='Gas Price',
        line=dict(color='orange'),
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Gas Price: {p:.2f}p/MWh" for d, p in zip(filtered_data['Date'], filtered_data['Gas Price'])],
        hovertemplate='%{text}<extra></extra>'
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
    return chart_figure

def ratio_chart(start_date=None, end_date=None, period_group='Daily'):
    filtered_data = filter_and_group_data(start_date, end_date, period_group)
    chart_figure = go.Figure()
    chart_figure.add_trace(go.Scatter(
        x=filtered_data['Date'],
        y=filtered_data['Ratio'],
        mode='lines+markers',
        name='Electricity/Gas Price Ratio',
        line=dict(color='green'),
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Ratio: {r:.2f}" for d, r in zip(filtered_data['Date'], filtered_data['Ratio'])],
        hovertemplate='%{text}<extra></extra>'
    ))
    chart_figure.update_layout(
        title='Electricity Price / Gas Price Ratio vs Date',
        xaxis_title='Date',
        yaxis_title='Ratio',
        hovermode='closest',
        template='plotly_dark',
        height=600
    )
    return chart_figure

