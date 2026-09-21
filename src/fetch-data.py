#Fetches and cleans the data from the GB electricity market, returning a DataFrame with the relevant columns.
from collections.abc import Callable
from datetime import date, datetime, timezone, timedelta
import numpy as np
from OSGridConverter import grid2latlong, OSGridReference
import pandas as pd
import sys
from functools import partial
from titlecase import titlecase
import traceback

from backend.gas import fetch_gas_data
from backend.generation import fetch_generation_and_prices, fetch_demand, merge_generators, create_elec_vs_gas_dataset, fetch_balancing_mechanism_data
from backend.policy import fetch_lccc_data
from backend.metrics import create_metrics
from figures.metric import Metric
from constants import INFLATORS, MANUAL_DATA_PATH, NESO_GENERATION_TYPES, RAW_DATA_PATH, PROCESSED_DATA_PATH, DATE_FIELD, DATETIME_FIELD
from datasources.supply import *
from datasources.policy import *
from datasources.system import *

def local_data_sources(process_only: bool) -> None:
    data = capacity_factors_source.fetch_data()
    data[DATE_FIELD] = pd.to_datetime(data[DATE_FIELD], format='%d/%m/%y', errors='coerce')
    
    capacity_factor_constant = 100000/(91.5*24)
    for fuel_type in ['Onshore Wind', 'Offshore Wind', 'Solar']:
        data[f'{fuel_type} Capacity Factor (%)'] = capacity_factor_constant * data[f'{fuel_type} Generation (GWh)'] / data[f'{fuel_type} Capacity (MW)'] 
    capacity_factors_source.save_data(data)

def create_rolling_quartely_totals(process_only: bool):
    print("Creating rolling quarterly totals...")
    gasvselec = gasvselec_dataset.load_data()
    cfd_settlements = cfd_settlements_source.load_data()
    cm_payments = cm_payments_source.load_data()
    bm_payments = bm_payments_source.load_data()

    gasvselec['Gas Cost'] = gasvselec['Gas Price'] * gasvselec['Gas'] * 2.5
    gasvselec['Wholesale Cost'] = gasvselec['Electricity Price'] * gasvselec['Total']

    cfd_settlements[DATE_FIELD] = pd.to_datetime(cfd_settlements['Settlement Date'], errors='coerce')
    cfd_settlements = cfd_settlements.groupby(DATE_FIELD).agg({'CfD Payments (£)': 'sum'}).reset_index()

    cm_payments[DATE_FIELD] = pd.to_datetime(cm_payments['Calendar Year'].astype(str) + '-' + cm_payments['Calendar Month'].astype(str) + "-01", errors='coerce')
    cm_payments = cm_payments[cm_payments['Capacity Payment Suspension Flag'] == 'Not Suspended']
    cm_payments = cm_payments.groupby(DATE_FIELD).agg({'Capacity Payment (£)': 'sum', "Auction Acquired Capacity Obligation (MW)": 'sum'}).reset_index()
    
    bm_payments["Total"] = bm_payments[['Energy Imbalance', 'Frequency Control', 'Positive Reserve', 'Constraints', 'Negative Reserve', 'Other']].sum(axis=1)

fetch_functions_list: list[tuple[Callable[[bool], None], str]] = [
    (fetch_generation_and_prices, "Generation and Prices Data"),
    (fetch_demand, "Demand Data"),
    (merge_generators, "Update List of Generators"),
    (fetch_balancing_mechanism_data, "Balancing Mechanism Data"),
    (fetch_gas_data, "Gas Data"),
    (fetch_lccc_data, "LCCC Data"),
    (create_elec_vs_gas_dataset, "Electricity vs Gas Data"),
    (local_data_sources, "Local Data Sources"),
    (create_metrics, "Create Metrics")
]

fetch_functions = {chr(65 + i): (func, desc) for i, (func, desc) in enumerate(fetch_functions_list)}
ALL = ''.join([key for key in fetch_functions.keys()])

def show_menu():
    print("Select the data to fetch and process. Available options:")
    for key, (func, description) in fetch_functions.items():
        print(f"{key}. {description}")
    print("#. All Data (default)")
    option = input(f"Enter the option letter (A-{chr(65 + len(fetch_functions) - 1)}, #): ").strip().upper()
    if option == '#' or option == '':
        option = ALL  # All options
    return option

if __name__ == "__main__":
    # If --fetch-all is passed as an argument, fetch all data
    if '--fetch-all' in sys.argv:
        option = ALL
    else:
        option = show_menu()

    process_only = False
    if '--process-only' in sys.argv:
        process_only = True

    for opt in option:
        if opt in fetch_functions:
            try:
                print(f"Fetching and processing: {fetch_functions[opt][1]}")
                fetch_functions[opt][0](process_only)
            except:
                # Print stack trace for debugging
                #print(f"Error occurred while processing {fetch_functions[opt][1]}: {e}")
                traceback.print_exc()
        else:
            print(f"Invalid option: {opt}. Skipping.")