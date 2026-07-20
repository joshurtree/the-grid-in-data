import os
import pandas as pd
from datetime import datetime, date
from backend.constants import RAW_DATA_DIR

def load_cfd_data() :
    cfd_data = pd.read_csv(os.path.join(RAW_DATA_DIR, 'cfd_settlements.csv'))
    cfd_data['Allocation_round'] = cfd_data['Allocation_round'].replace("Investment Contract", "Allocation Round 1")
    cfd_data['Settlement Date'] = pd.to_datetime(cfd_data['Settlement_Date'])
    cfd_data.rename(columns={'CFD_Payments_GBP': 'CFD Payments', 'Allocation_round': 'Allocation Round'}, inplace=True)
    # Replace "Allocation_Round" of "Investment Contract" with "Allocation Round 2" for consistency
    return cfd_data

data = load_cfd_data()
data['Year'] = data['Settlement Date'].dt.year 

def group_data(technology, allocation_rounds):
    grouped_data = data.copy()
    if technology != "All":
        grouped_data = grouped_data[grouped_data['Technology'] == technology]
    # Filter by allocation rounds
    if allocation_rounds:
        grouped_data = grouped_data[grouped_data['Allocation Round'].isin(allocation_rounds)]
    # Group the data by "Year" and "Allocation Round". Then sum the "CFD Payments" for each financial year
    grouped_data = (grouped_data.groupby(['Year', 'Allocation Round'], observed=True)['CFD Payments'].sum()/1e6).reset_index()
    grouped_data.rename(columns={'CFD Payments': 'CFD Payments (£ million)'}, inplace=True)
    #print(f'[DEBUG] Grouped data from {start_date.date()} to {end_date.date()}:\n{grouped_data}')
    return grouped_data

def update_chart(state):
    state.grouped_data = group_data(state.technology, state.allocation_rounds)

technology: str = "All"
available_technologies: list = ["All"] + sorted(data['Technology'].unique().tolist())
allocation_rounds: list = sorted(data['Allocation Round'].unique().tolist())
grouped_data: pd.DataFrame = group_data(technology, allocation_rounds)

show_table: bool = False

colours = {
    "Allocation Round 1": "#1f77b4",  # Blue
    "Allocation Round 2": "#ff7f0e",  # Orange
    "Allocation Round 3": "#2ca02c",  # Green
    "Allocation Round 4": "#d62728",  # Red
    "Allocation Round 5": "#9467bd",  # Purple
    "Allocation Round 6": "#8c564b",  # Brown
    "Allocation Round 7": "#e377c2",  # Pink
    "Allocation Round 8": "#7f7f7f",  # Gray
}
