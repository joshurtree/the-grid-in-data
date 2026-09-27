from datetime import datetime
import os
import pandas as pd
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from figures.chartset import Chart
from constants import DATE_FIELD, INFLATORS, RAW_DATA_PATH, MANUAL_DATA_PATH
from  datasources.policy import cm_auctions_source, cm_payments_source, cm_forecast_source


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
    df = cm_auctions_source.load_data()

    # Apply the selected inflator to adjust the prices
    df['Adjusted Price'] = df.apply(lambda row: row['Price'] * inflator_functions[inflator_type](row['Auction Year'], row['Delivery Year'], row['Price Year']), axis=1)
    
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
            y=auction_data['Adjusted Price'],
            mode='lines',
            name=str(auction) + " Price",
            marker=dict(size=10, opacity=0.7, symbol=marker)
        ), secondary_y=True)

    # Create a stacked bar chart for the capacity securced in each auction
    auction_data = df[df['Auction Type'] == auction]
    for auction in auctions:
        auction_data = df[df['Auction Type'] == auction]
        fig.add_trace(go.Bar(
            x=auction_data['Auction Year'],
            y=auction_data['Capacity awarded'],
            name=str(auction) + " Capacity",
            marker=dict(opacity=0.5),
        ), secondary_y=False)

    fig.update_layout(
        barmode='stack',
        title='CM Auction Prices',
        xaxis_title='Delivery Year',
        yaxis_title='Price (£/kW/year)',
        legend=dict(x=1.05, y=1, traceorder='normal'),
        grid=dict(rows=1, columns=1)
    )
    fig.update_yaxes(title_text="Price (£/kW/year)", secondary_y=True)
    fig.update_yaxes(title_text="Capacity Secured (MW)", secondary_y=False)

    return Chart(
        cm_auctions_source,
        df,
        fig,
        title="CM Auction Prices",
        description="This chart shows the Capacity Market auction prices over time, broken down by auction. Each auction is represented by a different symbol, and the capacity secured in each auction is shown as a stacked bar chart."
    )

def create_cm_payments(inflator_type='Delivery Year') -> Chart:
    """
    Create a DataFrame of CM payments for each auction year, adjusted by the selected inflator.

    Use `raw/capacity_obligation_by_auction.csv` to calculate the total payments for each auction year, applying the selected inflator type to adjust the prices accordingly.
    For dates beyond the end of the data, use the cm-auctions.csv data to estimate payments based on the last known auction prices and durations.
    """   
    # Read the data
    df = cm_payments_source.load_data()
    #df[DATE_FIELD] = pd.to_datetime(f"{df['Calendar Month']} {df['Calendar Year']}", format='%B %Y')
    #df = df[(df[DATE_FIELD] >= start_date) & (df[DATE_FIELD] <= end_date)]
    df = df[df['Capacity Payment Suspension Flag'] == 'Not Suspended']
    df = df.groupby('Calendar Year')['Capacity Payment (£)'].sum().reset_index()

    # Append the auction data to estimate payments for future years by multiplying the price with the Quantity from the last known year
    # and applying the inflator to adjust the price to the delivery year.
    # auction_df = pd.read_csv(os.path.join(MANUAL_DATA_PATH, 'cm-auctions.csv'))
    # auction_df = auction_df[auction_df['Delivery Year'] > df['Calendar Year'].max()]

    # for _, row in auction_df.iterrows():
    #     start_year = row['Delivery Year']
    #     duration = row['Duration']
    #     estimated_payments = row['Price']*row['Quantity'] * inflator_functions['Delivery Year'](row['Auction Year'], start_year, row['Price Year'])*1000

    #     for year_offset in range(duration):
    #         delivery_year = start_year + year_offset
    #         df = pd.concat([df, pd.DataFrame({'Calendar_Year': [delivery_year], 'Capacity_Payment_GBP': [estimated_payments]})], ignore_index=True)

    forcast_df = cm_forecast_source.load_data().groupby('Calendar Year')['Monthly CM Forecast Cost (£)'].sum().reset_index()
    #forcast_df = forcast_df[DATE_FIELD > df[DATE_FIELD].max()]
    
    # Create the figure
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['Calendar Year'],
        y=df['Capacity Payment (£)'],
        name='Actual Payments',
        marker_color='indianred'
    ))

    fig.add_trace(go.Bar(
        x=forcast_df['Calendar Year'],
        y=forcast_df['Monthly CM Forecast Cost (£)'],
        name='Forecasted Payments',
        marker_color='lightsalmon'
    ))

    fig.update_layout(
        title='CM Payments by Delivery Year',
        barmode='stack',
        xaxis_title='Calendar Year',
        yaxis_title='Total Payments (£)',
        legend=dict(x=1.05, y=1, traceorder='normal'),
        grid=dict(rows=1, columns=1)
    )

    return Chart(
        cm_payments_source, 
        df,
        fig, 
        title="CM Payments by Delivery Year", 
        description="This chart shows the total Capacity Market payments made to generators over time, broken down by delivery year. It includes both actual payments and forecasted payments based on auction data."
    )