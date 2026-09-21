import pandas as pd
import requests

from datasources.policy import ets_source, carbon_taxes_dataset
from constants import MANUAL_DATA_PATH

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch_current_ets():
    """
    Fetches the current Emissions Trading System (ETS) data and updates the corresponding metric.
    """
    ets_data = pd.read_csv(os.path.join(MANUAL_DATA_PATH, "ets.csv"), parse_dates=["Date"])
    ets_source.save_data(ets_data)

def calculate_gas_taxes():
    """
    Calculates the gas taxes based on the ETS data and updates the corresponding metric.
    """
    ets_data, generation_data = carbon_taxes_dataset.base_data()

    # Assuming the ETS price is in £/tonne CO2 and we have a conversion factor for gas
    carbon_support_price = 18
    conversion_factor = 0.184/0.4

    # Calculate the gas tax based on the ETS price and the conversion factor
    generation_data["Carbon Tax (£/MWh)"] = generation_data["ETS Price (£/tonne CO2)"] * conversion_factor
