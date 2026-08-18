import os
import pandas as pd
from datetime import datetime, date
from backend.constants import RAW_DATA_DIR
from plotly import graph_objects as go

base_data = pd.read_csv(os.path.join(RAW_DATA_DIR, 'cfd_settlements.csv'))
base_data.rename(columns={'Settlement_Date': 'Settlement Date', 'CFD_Payments_GBP': 'CFD Payments', 'Allocation_round': 'Allocation Round'}, inplace=True)
base_data['Allocation Round'] = base_data['Allocation Round'].replace("Investment Contract", "Allocation Round 1.5")
base_data['Settlement Date'] = pd.to_datetime(base_data['Settlement Date'])
base_data['Year'] = base_data['Settlement Date'].dt.year
base_data['CFD Payments per MWh'] = base_data['CFD Payments'] / base_data['CFD_Generation_MWh']
technologies = base_data['Technology'].unique().tolist()
rounds = base_data['Allocation Round'].unique().tolist()

class CFDData:
    def __init__(self, start_date: datetime = None, end_date: datetime = None, technology: list = None, allocation_rounds: list = None):
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.technology = technology
        self.allocation_rounds = allocation_rounds
        print(f"Initialized CFDData with start_date={self.start_date}, end_date={self.end_date}, technology={self.technology}, allocation_rounds={self.allocation_rounds}")

    def filter_data(self):
        data = base_data.copy()
        print(self.start_date, self.end_date, self.technology, self.allocation_rounds)
        data = data[(data['Settlement Date'] >= self.start_date) & (data['Settlement Date'] <= self.end_date)]
        print(f"Filtered data from {len(base_data)} to {len(data)} records based on date range.")

        # Filter by allocation rounds
        if self.allocation_rounds:
            data = data[data['Allocation Round'].isin(self.allocation_rounds)]
        print(f"Filtered data from {len(base_data)} to {len(data)} records based on allocation rounds.")

        if self.technology:
            data = data[data['Technology'].isin(self.technology)]
        print(f"Filtered data from {len(base_data)} to {len(data)} records based on date range, technology, and allocation rounds.")
        return data

    def group_data(self, group_by=['Technology', 'Allocation Round']):
        data = self.filter_data()

        # Group the data by "Technology" and "Allocation Round".
        aggregation_functions = {
            'CFD Payments': lambda x: x.sum()/1e6,  # Sum the CFD Payments and convert to millions
            'CFD Payments per MWh': 'mean',  # Average the CFD Payments per MWh
        }
        grouped_data = data.groupby(group_by).agg(aggregation_functions).reset_index()
        grouped_data.rename(columns={'CFD Payments': 'CFD Payments (£ million)'}, inplace=True)

        return grouped_data

    def create_cfd_chart(self):
        grouped_data = self.group_data()
        fig = go.Figure()
        for technology in grouped_data['Technology'].unique():
            tech_data = grouped_data[grouped_data['Technology'] == technology]
            fig.add_trace(go.Bar(
                x=tech_data['Allocation Round'],
                y=tech_data['CFD Payments (£ million)'],
                name=technology,
                marker_color=colours.get(technology, '#000000')  # Default to black if not found
            ))
        fig.update_layout(
            title=f'CFD Payments by Technology and Allocation Round',
            xaxis_title='Technology',
            yaxis_title='CFD Payments (£ million)',
            barmode='group'
        )
        return fig

    # Create a line chart of CFD payments paid vs strike price 
    def create_strike_price_chart(self):
        data = self.group_data(group_by=['Technology', 'Strike_Price_GBP_Per_MWh'])
        fig = go.Figure()
        for technology in data['Technology'].unique():
            tech_data = data[data['Technology'] == technology]
            # Calculate the CFD payments paid based on the strike price
            fig.add_trace(go.Scatter(
                x=tech_data['Strike_Price_GBP_Per_MWh'],
                y=tech_data['CFD Payments per MWh'],
                mode='markers+lines',
                name=technology,
                line=dict(color=colours.get(technology, '#000000')),                 
                hovertemplate='Strike Price: %{x}<br>CFD Payments: %{y}<extra></extra>'
            ))
        fig.update_layout(
            title=f'CFD Payments Paid vs Strike Price',
            xaxis_title='Strike Price (£/MWh)',
            yaxis_title='Average CFD Payments Paid (£/MWh)',
        )
        return fig

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
