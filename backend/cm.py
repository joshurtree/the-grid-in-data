from datetime import datetime
import os
import pandas as pd
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from backend.constants import INFLATORS, RAW_DATA_DIR, MANUAL_DATA_DIR


auction_inflator = lambda ay, dy, py: INFLATORS.get(ay, 1.0) / INFLATORS.get(py, 1.0)
delivery_inflator = lambda ay, dy, py: INFLATORS.get(dy, 1.0) / INFLATORS.get(py, 1.0)
constant_inflator = lambda ay, dy, py: INFLATORS.get(datetime.now().year, 1.0) / INFLATORS.get(py, 1.0)

inflator_functions = {
    'Delivery Year': delivery_inflator,
    'Auction Year': auction_inflator,
    'Constant': constant_inflator
}

def create_cm_auction_scatter(inflator_type='Delivery Year'):
    """
    Create a scatter chart of CM auction prices over delivery years.
    Each auction is represented by a different symbol.
    """
    # Read the data
    df = pd.read_csv('data/raw/cm-auctions.csv')

    
    # Create scatter plot
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Get unique auctions and assign different markers
    auctions = df['Auction Type'].unique()
    markers = ['circle', 'square' ]    
    for i, auction in enumerate(auctions):
        auction_data = df[df['Auction Type'] == auction]
        marker = markers[i % len(markers)]
        fig.add_trace(go.Scatter(
            x=auction_data['Auction Year'],
            y=auction_data['Price'],
            mode='markers+lines',
            name=auction,
            marker=dict(size=10, opacity=0.7, symbol=marker)
        ), secondary_y=False)

    # Create a stacked bar chart for the capacity securced in each auction
    auction_data = df[df['Auction Type'] == auction]
    for auction in auctions:
        auction_data = df[df['Auction Type'] == auction]
        fig.add_trace(go.Bar(
            x=auction_data['Auction Year'],
            y=auction_data['Capacity awarded'],
            name=auction,
            marker=dict(opacity=0.5),
        ), secondary_y=True)

    fig.update_layout(
        barmode='stack',
        title='CM Auction Prices by Delivery Year',
        xaxis_title='Delivery Year',
        yaxis_title='Price (£/kW/year)',
        legend=dict(x=1.05, y=1, traceorder='normal'),
        grid=dict(rows=1, columns=1)
    )

    return fig

def create_cm_payments():
    """
    Create a DataFrame of CM payments for each delivery year, adjusted by the selected inflator.
    
    Use `raw/capacity_obligation_by_auction.csv` to calculate the total payments for each delivery year, applying the selected inflator type to adjust the prices accordingly.
    For dates beyond the end of the data, use the cm-auctions.csv data to estimate payments based on the last known auction prices and durations.
    """

        
    # Read the data
    df = pd.read_csv(os.path.join(RAW_DATA_DIR, 'capacity_obligation_by_auction.csv'))
    df = df[df['Capacity_Payment_Suspension_Flag'] == 'Not Suspended']
    df = df.groupby('Calendar_Year')['Capacity_Payment_GBP'].sum().reset_index()

    # Append the auction data to estimate payments for future years by multiplying the price with the Quantity from the last known year
    # and applying the inflator to adjust the price to the delivery year.
    # auction_df = pd.read_csv(os.path.join(MANUAL_DATA_DIR, 'cm-auctions.csv'))
    # auction_df = auction_df[auction_df['Delivery Year'] > df['Calendar_Year'].max()]
    
    # for _, row in auction_df.iterrows():
    #     start_year = row['Delivery Year']
    #     duration = row['Duration']
    #     estimated_payments = row['Price']*row['Quantity'] * inflator_functions['Delivery Year'](row['Auction Year'], start_year, row['Price Year'])*1000

    #     for year_offset in range(duration):
    #         delivery_year = start_year + year_offset
    #         df = pd.concat([df, pd.DataFrame({'Calendar_Year': [delivery_year], 'Capacity_Payment_GBP': [estimated_payments]})], ignore_index=True)

    forcast_df = pd.read_csv(os.path.join(RAW_DATA_DIR, 'neso_capacity_market_forecast.csv')).groupby('Calendar_Year')['Monthly_CM_Forecast_Cost_GBP'].sum().reset_index()

    # Create the figure
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['Calendar_Year'],
        y=df['Capacity_Payment_GBP'],
        name='CM Payments',
        marker_color='indianred'
    ))

    fig.add_trace(go.Bar(
        x=forcast_df['Calendar_Year'],
        y=forcast_df['Monthly_CM_Forecast_Cost_GBP'],
        name='Forecasted Payments',
        marker_color='lightsalmon'
    ))

    fig.update_layout(
        title='CM Payments by Delivery Year',
        barmode='stack',
        xaxis_title='Calendar_Year',
        yaxis_title='Total Payments (£)',
        legend=dict(x=1.05, y=1, traceorder='normal'),
        grid=dict(rows=1, columns=1)
    )

    return fig