import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from io import BytesIO
import re

from backend.nationalgas import STORAGE, NBP_GAS_PRICE, DEMAND, update_national_gas_datasource
from constants import DATE_FIELD, MANUAL_DATA_PATH
from  datasources.supply import *

http_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch_gas_prices() :
    print('Fetching system prices from ONS and National Gas...')
    try:
        if not ons_system_gas_price_source.exists():            
            # System prices are published on Thursday
            link = 'https://www.ons.gov.uk/file?uri=/economy/economicoutputandproductivity/output/datasets/systemaveragepricesapofgas/2026/previous/v34/systemaveragepriceofgasdataset270826.xlsx'
            # Use requests to fetch the Excel file from the ONS website
            response = requests.get(link, headers=http_headers)
            response.raise_for_status()
            ons_prices = pd.read_excel(BytesIO(response.content), "1.Daily SAP Gas", skiprows=4)
            ons_prices.drop(columns=['SAP seven-day rolling average'], inplace=True)
            ons_prices.rename(columns={'SAP actual day': 'Price (£/MWh)'}, inplace=True)
            ons_prices["Price (£/MWh)"] = ons_prices["Price (£/MWh)"] * 10

            ons_system_gas_price_source.save_data(ons_prices)
    except Exception as e:
        print(f"Error fetching ONS gas prices: {e}")
        ons_prices = ons_system_gas_price_source.load_data()

def fetch_national_gas_data() :
    print('Fetching gas data from National Gas API...')
    update_national_gas_datasource(gas_storage_source, STORAGE)
    update_national_gas_datasource(ngas_system_gas_price_source, NBP_GAS_PRICE)
    update_national_gas_datasource(gas_demand_source, DEMAND)

def fetch_gas_storage_capacity_data() :
    gas_storage_capacity_data = pd.read_csv(os.path.join(MANUAL_DATA_PATH, "gas_storage_capacity.csv"))
    gas_storage_capacity_data[DATE_FIELD] = pd.to_datetime(gas_storage_capacity_data['Year'].astype(str) + '-01-01', errors='coerce')
    gas_storage_capacity_source.save_data(gas_storage_capacity_data)

def fetch_average_price(page: BeautifulSoup, date: datetime, median_price: float) -> float:
    ''' 
    Average price is part of the text in the form of 
    <p>Natural Gas price forecast  for <strong>September 2026</strong>. 
        In the beginning the price at 182 GBp. Maximum 267, minimum 177. The averaged price 218. 
        Natural Gas price at the end of the month 247, the change for September 35.7%.
    </p>
    '''
    p_tags = page.find_all("p")
    for p in p_tags:
        strong_tag = p.find("strong")
        if strong_tag and date.strftime("%B %Y") in strong_tag.get_text():
            match = re.search(r"The averaged price (\d+)", p.get_text())
            if match:
                return float(match.group(1))
    return median_price  # Return median price if no average found

def fetch_gas_price_forecast():
    resp = requests.get("https://poundf.co.uk/uk-natural-gas", headers=http_headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    tgs = soup.find_all("table")
    if len(tgs) < 2:
        raise RuntimeError(f"Not enough <table> elements ({len(tgs)}) found on the page")
    target = tgs[1]

    rows = []
    year = None
    for tr in target.find_all("tr"):
        cols = [cell.get_text(strip=True) for cell in tr.find_all(["th", "td"])]

        if len(cols) == 1:
            # Year header row, extract year
            year = cols[0]
        elif year is not None:
            # Data row, prepend year to the first column
            row = []
            date = datetime.strptime(f"{year} {cols[0]}", "%Y %b")
            row.append(date)

            min_max = cols[2].split('-')

            # Third column is min-max range, split it into two separate rows for min and max
            if len(min_max) == 2:
                median_price = (int(min_max[0]) + int(min_max[1])) / 2
                row.append(fetch_average_price(soup, date, median_price))
                row.append(min_max[0])
                row.append(min_max[1])
            rows.append(row)

    if not rows:
        raise RuntimeError("No data rows found in the table")

    future_gas_prices = pd.DataFrame(rows, columns=[DATE_FIELD, "Price", "Min", "Max"])

    # Convert from p/therm to p/kWh and round to 4 decimal places
    for col in ['Price', 'Min', 'Max']:
        future_gas_prices[col] = pd.to_numeric(future_gas_prices[col], errors='coerce')/2.9307
    gas_price_forecast_source.save_data(future_gas_prices)

def process_gas_prices():
    ons_gas_prices, ngas_prices = daily_gas_prices_dataset.base_data()

    ngas_prices = ngas_prices[ngas_prices[DATE_FIELD] > ons_gas_prices[DATE_FIELD].max()]
    past_gas_prices = pd.concat([ons_gas_prices, ngas_prices]).sort_values(by=DATE_FIELD).reset_index(drop=True)
    daily_gas_prices_dataset.save_data(past_gas_prices)

    _, future_gas_prices = monthly_gas_prices_dataset.base_data()

    # Ensure the date column is a proper datetime type, drop invalid rows and resample by month start.
    past_gas_prices[DATE_FIELD] = pd.to_datetime(past_gas_prices[DATE_FIELD], errors='coerce')
    past_gas_prices = past_gas_prices.dropna(subset=[DATE_FIELD]).sort_values(by=DATE_FIELD).reset_index(drop=True)

    # Combine past and future gas prices, ensuring no duplicates and sorting by date
    combined_gas_prices = pd.concat([past_gas_prices, future_gas_prices]).drop_duplicates(subset=DATE_FIELD).sort_values(by=DATE_FIELD).reset_index(drop=True)
    monthly_gas_prices_dataset.save_data(combined_gas_prices)

def create_gas_storage_dataset():
    storage_data, storage_capacity_data, demand_data = gas_storage_dataset.base_data()

    storage_capacity_data.set_index('Year', inplace=True)
    print(storage_capacity_data.columns)
    # Take the rolling one month daily average demand to calculate the number of days of storage remaining
    demand_data[DATE_FIELD] = pd.to_datetime(demand_data[DATE_FIELD], errors='coerce')
    demand_data = demand_data.dropna(subset=[DATE_FIELD]).sort_values(by=DATE_FIELD).reset_index(drop=True)
    demand_data = demand_data.set_index(DATE_FIELD).rolling('30D').mean().reset_index()
    storage_data = storage_data.merge(demand_data, on=DATE_FIELD, how='left')
    
    storage_data['Year'] = storage_data[DATE_FIELD].dt.year
    storage_data['Gas Reserves (Days)'] = storage_data['Gas Reserves (GWh)'] / (storage_data['Gas Demand (GWh)'])
    storage_data['Gas Capacity (GWh)'] = storage_data['Year'].map(storage_capacity_data['Gas Capacity (GWh)'])
    storage_data['Gas Capacity (Days)'] = storage_data['Gas Capacity (GWh)'] / (storage_data['Gas Demand (GWh)'])
    storage_data.drop(columns=['Year'], inplace=True)
    storage_data.sort_values(by=DATE_FIELD, inplace=True)
    
    gas_storage_dataset.save_data(storage_data)

def fetch_gas_data(process_only: bool) -> None:
    if not process_only:
        fetch_gas_prices()
        fetch_gas_price_forecast()
        fetch_national_gas_data()
        fetch_gas_storage_capacity_data()

    process_gas_prices()
    create_gas_storage_dataset()
