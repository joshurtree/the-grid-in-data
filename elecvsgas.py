from dataclasses import dataclass
from datetime import datetime, date
import os
import pandas as pd
import plotly.graph_objects as go
from taipy.gui import Gui
import taipy.gui.builder as tgb
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

    # Add trendline for electricity price
    trendline_electricity = create_trendline(filtered_data['Date'].map(datetime.toordinal), filtered_data['Electricity Price'])

    chart_figure.add_trace(go.Scatter(
        x=filtered_data['Date'],
        y=trendline_electricity,
        mode='lines',
        name='Electricity Price Trendline',
        line=dict(color='green', dash='dash')
    ), secondary_y=False)

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

start_date: date = date.today() - pd.DateOffset(years=1)  # Default to one year ago
end_date: date = date.today()
date_range = [start_date, end_date]
show_ratio: bool = False
period_group: str = 'Day'
chart_figure: go.Figure = create_chart(start_date, end_date, period_group)

def update_chart(state):
    state.chart_figure = create_chart(state.start_date, state.end_date, state.period_group) if not state.show_ratio else ratio_chart(state.start_date, state.end_date, state.period_group)
    #state.table = group_by_generation(data[(data['DATETIME'] >= pd.to_datetime(state.start_date)) & (data['DATETIME'] <= pd.to_datetime(state.end_date))])

with tgb.Page() as elecvsgas_page:
    tgb.text(value="# GB Electricity Prices vs Gas Prices", mode="md")
    with tgb.part(class_name="card"):
        tgb.date_range("{date_range}", label="Date Range", min=date(2016, 6, 30), max=date.today(), format='dd/MM/yyyy', on_change=update_chart)
        with tgb.layout(columns="1 1"):
            with tgb.part():
                tgb.selector("{period_group}", label="Group By", lov=list(PERIOD_GROUPS.keys())[1:], on_change=update_chart, dropdown=True)
            with tgb.part():
                tgb.toggle(value="{show_ratio}", label="Show Ratio", on_change=update_chart)
    with tgb.part(class_name="card"):
        #with tgb.part(render="{not show_table}"):
        tgb.chart(figure="{chart_figure}", title=f"Wholesale Electricity Price vs Gas Price", xaxis_title="Date", yaxis_title="Price (£/MWh)", hovermode="closest", template="plotly_dark")
        #with tgb.part(render="{show_table}"):
        #    tgb.table("{table}", title="Average Generation by Price Group", columns=table.columns.tolist(), number_format="%.2f", show_all=True)
    with tgb.part(class_name="card"):
        tgb.text(value="## Data Source", mode="md")
        tgb.text(value="Electricity prices are sourced from the [Elexon Portal](https://www.elexonportal.co.uk/), while gas prices are sourced from the ONS's [System Average Price of Gas](https://www.ons.gov.uk/economy/economicoutputandproductivity/output/datasets/systemaveragepricesapofgas).", mode="md")