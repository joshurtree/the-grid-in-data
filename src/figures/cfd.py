import os
import pandas as pd
from datetime import datetime, date
from constants import RAW_DATA_PATH
from  datasources.policy import cfd_settlements_source, cfd_contracts_source
from plotly import graph_objects as go
from figures.chartset import Chart

colours = {
    "Allocation Round 1": "#1f77b4",  # Blue
    "Allocation Round 2": "#ff7f0e",  # Orange
    "Allocation Round 3": "#2ca02c",  # Green
    "Allocation Round 4": "#d62728",  # Red
    "Allocation Round 5": "#9467bd",  # Purple
    "Allocation Round 6": "#8c564b",  # Brown
    "Allocation Round 7": "#e377c2",  # Pink
    "Allocation Round 8": "#7f7f7f",  # Gray

    # Technology colors
    "Offshore Wind": "#1f77b4",  # Blue
    "Onshore Wind": "#ff7f0e",  # Orange
    "Solar PV": "#2ca02c",  # Green
    "Dedicated Biomass": "#d62728",  # Red
    "Biomass Conversion": "#9467bd",  # Purple
    "Energy from Waste": "#8c564b",  # Brown
}

base_data = cfd_settlements_source.load_data()
base_data['Allocation Round'] = base_data['Allocation Round'].apply(lambda x: "Pre-Allocation Round 1" if x == "Investment Contract" else x)
filtered_data = base_data.copy()

def get_available_technologies():
    return base_data['Technology'].unique().tolist()

def get_available_allocation_rounds():
    return base_data['Allocation Round'].unique().tolist()

def filter_data(start_date: date, end_date: date, technologies: list, allocation_rounds: list):
    data = base_data.copy()
    data = data[(data['Settlement Date'] >= pd.to_datetime(start_date)) & (data['Settlement Date'] <= pd.to_datetime(end_date))]
    print(f"Filtered data from {len(base_data)} to {len(data)} records based on date range.")

    # Filter by allocation rounds
    if allocation_rounds:
        data = data[data['Allocation Round'].isin(allocation_rounds)]
    print(f"Filtered data from {len(data)} to {len(data)} records based on allocation rounds.")

    if technologies:
        data = data[data['Technology'].isin(technologies)]
    print(f"Filtered data from {len(data)} to {len(data)} records based on date range, technology, and allocation rounds.")
    global filtered_data
    filtered_data = data

def group_data(group_by=['Technology', 'Allocation Round']):
    data = filtered_data
    # Group the data by "Technology" and "Allocation Round".
    aggregation_functions = {
        'CfD Payments (£)': lambda x: x.sum()/1e6,  # Sum the CFD Payments and convert to millions
        'CfD Payments (£/MWh)': 'mean',  # Average the CFD Payments per MWh
    }
    grouped_data = data.groupby(group_by).agg(aggregation_functions).reset_index()
    grouped_data.rename(columns={'CfD Payments (£)': 'CfD Payments (£ million)'}, inplace=True)

    return grouped_data

def create_cfd_chart():
    grouped_data = group_data()
    fig = go.Figure()
    for technology in grouped_data['Technology'].unique():
        tech_data = grouped_data[grouped_data['Technology'] == technology]
        fig.add_trace(go.Bar(
            x=tech_data['Allocation Round'],
            y=tech_data['CfD Payments (£ million)'],
            name=technology,
            marker_color=colours.get(technology, '#000000'),  # Default to black if not found
            text=tech_data['CfD Payments (£ million)'].apply(lambda x: f'£{x:,.2f} million'),
            hovertemplate='CfD Payments: %{text}<extra></extra>',
        ))
    fig.update_layout(
        title=f'CfD Payments by Technology and Allocation Round',
        xaxis_title='Allocation Round',
        yaxis_title='CfD Payments (£ million)',
        barmode='group',
        hovermode='x'
    )
    return Chart(
        cfd_settlements_source, 
        fig, 
        title="CfD Payments by Technology and Allocation Round", 
        description="This chart shows the total CFD payments made to generators over time, broken down by technology and allocation round."
    )

# Create a line chart of CFD payments paid vs strike price 
def create_strike_price_chart():
    data = group_data(['Technology', 'Strike Price (£/MWh)'])
    fig = go.Figure()
    for technology in data['Technology'].unique():
        tech_data = data[data['Technology'] == technology]
        
        # Calculate the CFD payments paid based on the strike price
        fig.add_trace(go.Scatter(
            x=tech_data['Strike Price (£/MWh)'],
            y=tech_data['CfD Payments (£/MWh)'],
            name=technology,
            mode='markers',
            marker_color=colours.get(technology, '#000000'),
            hovertemplate='Strike Price: %{x}<br>CfD Payments: £%{y}/MWh<extra></extra><br>Technology: ' + technology,
        ))
    fig.update_layout(
        title=f'CfD Payments Paid vs Strike Price',
        xaxis_title='Strike Price (£/MWh)',
        yaxis_title='Average CfD Payments Paid (£/MWh)',
        hovermode='closest'
    )
    return Chart(
        cfd_settlements_source,
        fig,
        title="CfD Payments Paid vs Strike Price",
        description="This chart shows the relationship between the strike price and the average CFD payments paid to generators, broken down by technology."
    )

generators = cfd_contracts_source.load_data()
generators.rename(columns=dict([(name, name.replace("_", " ")) for name in generators.columns]), inplace=True)
status_mapping = {
    'Live (Post-FIC)': 'Live',
    'Live (Pre-FIC)': 'Live',
    'Pre-Start Date': 'Under Construction',
    'Pre-MDD': 'Planned',
    'Terminated': 'Terminated'
}
generators['Status'] = generators['Status'].apply(lambda x: status_mapping.get(x, x))
generators['Expected Start Date'] = pd.to_datetime(generators['Expected Start Date'], errors='coerce').dt.date

def get_available_statuses():
    return generators['Status'].unique().tolist()

def show_generators(search_term: str = "", status: str = "All"):
    filtered_generators = generators.copy()
    if search_term:
        filtered_generators = filtered_generators[
            filtered_generators.apply(
                lambda row: search_term.lower() in str(row['Generator Name']).lower() or
                            search_term.lower() in str(row['Technology']).lower(),
                axis=1
            )
        ]
    if status != "All":
        filtered_generators = filtered_generators[filtered_generators['Status'] == status]

    return Chart(cfd_settlements_source, 
                 filtered_generators, 
                 title="List of Generators", 
                 description="This table shows the list of generators participating in the CFD scheme, along with their status and expected start date."
                )
