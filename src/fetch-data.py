#Fetches and cleans the data from the GB electricity market, returning a DataFrame with the relevant columns.
from collections.abc import Callable
from datetime import date, datetime, timezone, timedelta
import numpy as np
from OSGridConverter import grid2latlong, OSGridReference
import os
import pandas as pd
import sys
import shutil
from titlecase import titlecase
import traceback

from backend.gas import fetch_gas_data
from backend.generation import create_generation_datasets, fetch_generation_and_prices, fetch_demand, merge_generators, create_elec_vs_gas_dataset, fetch_balancing_mechanism_data
from backend.policy import fetch_lccc_data
from backend.metrics import create_metrics
from backend.capacity_factors import create_capacity_factor_data
from figures.metric import Metric
from constants import METRIC_PATH, RAW_DATA_PATH, PROCESSED_DATA_PATH
from datasources.supply import *
from datasources.policy import *
from datasources.system import *

fetch_functions_list: list[tuple[Callable[[bool], None], str]] = [
    (fetch_generation_and_prices, "Generation and Prices Data"),
    (fetch_demand, "Demand Data"),
    (merge_generators, "Update List of Generators"),
    (fetch_balancing_mechanism_data, "Balancing Mechanism Data"),
    (fetch_gas_data, "Gas Data"),
    (fetch_lccc_data, "LCCC Data"),
    (create_generation_datasets, "Generation Datasets"),
    (create_capacity_factor_data, "Create Capacity Factor Data"),
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

    # Move the directories in `data/manual/base-data` to `data`
    if not os.path.exists('data/raw'):    
        for dir_name in os.listdir('data/manual/base-data'):
            shutil.move(os.path.join('data/manual/base-data', dir_name), 'data')
        
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