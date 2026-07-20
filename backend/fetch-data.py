#Fetches and cleans the data from the GB electricity market, returning a DataFrame with the relevant columns.
import argparse
from datetime import datetime, timezone, timedelta
from io import StringIO
import os
from OSGridConverter import grid2latlong, OSGridReference
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm
from backend.bmrs import fetch_demand, fetch_FPN

from backend.constants import MANUAL_DATA_DIR, NESO_GENERATION_TYPES, RAW_DATA_DIR, TRANSFORMED_DATA_DIR

def fetch_gas_prices() :
    print('Fetching gas prices from ONS...')
    date = datetime.now(timezone.utc)
    uri = f"/economy/economicoutputandproductivity/output/datasets/systemaveragepricesapofgas/{date.year}/systemaveragepriceofgasdataset{date.strftime('%d%m%y')}.xlsx"
    gas_prices = pd.read_excel(f"https://www.ons.gov.uk/file?uri={uri}", "1.Daily SAP Gas", skiprows=4)
    gas_prices['Date'] = pd.to_datetime(gas_prices['Date'])
    gas_prices = gas_prices.set_index('Date')
    gas_prices.to_json(os.path.join(RAW_DATA_DIR, 'gas_prices.json'), orient='records', indent=2)

def fetch_embedded_generation():
    # Load data from CSV files
    print('Fetching embedded generation data from Neso API...')
    embedded_generation = pd.read_csv('https://api.neso.energy/dataset/91c0c70e-0ef5-4116-b6fa-7ad084b5e0e8/resource/db6c038f-98af-4570-ab60-24d71ebd0ae5/download/202607090125_embedded_forecast.csv')
    #embedded_generation['DATETIME'] = pd.to_datetime(embedded_generation['DATETIME'] + 'Z')
    #embedded_generation = embedded_generation.set_index('DATETIME')
    embedded_generation.to_json(os.path.join(RAW_DATA_DIR, 'embedded_generation.json'), orient='records', indent=2)

def fetch_demand():
    print('Fetching demand data from Elexon API...')
    demand = fetch_demand(datetime.now(timezone.utc))
    demand.to_json(os.path.join(RAW_DATA_DIR, 'demand.json'), orient='records', indent=2)

def fetch_generation():
    # Load data from CSV files
    print('Fetching generation data from Neso API...')
    generation = pd.read_csv('https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/resource/f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv')
    generation['DATETIME'] = pd.to_datetime(generation['DATETIME'] + 'Z')
    generation = generation.set_index('DATETIME')
    generation.to_csv(os.path.join(RAW_DATA_DIR, 'generation.csv'))
    return generation

def fetch_prices():
    print('Fetching market prices from Elexon API...')
    raw_prices = pd.DataFrame()
    path = os.path.join(RAW_DATA_DIR, 'market-prices.csv')
    start_date = datetime(2017, 1, 1, tzinfo=timezone.utc)

    if os.path.exists(path) :
        # Load data from CSV files
        raw_prices = pd.read_csv(path)
        start_date = pd.to_datetime(raw_prices['StartTime']).max()

    # Fetch additional prices from Elexon API if needed
    date_ranges = pd.date_range(start=start_date, end=datetime.now(timezone.utc), freq='7D')
    progress_bar = tqdm(total=len(date_ranges), desc='Fetching market prices', unit='request')
    for start in date_ranges:
        end = start + timedelta(days=7)
        response = requests.get("https://data.elexon.co.uk/bmrs/api/v1/balancing/pricing/market-index", params={'format': 'csv', 'from': start, 'to': end})

        if response.status_code == 200:
            raw_prices = pd.concat([raw_prices, pd.read_csv(StringIO(response.content.decode('utf-8')))], ignore_index=True)
        else:
            raise Exception(f"Failed to retrieve data for {start} to {end}: {response.status_code}")
        progress_bar.update(1)
    progress_bar.close()
    raw_prices.to_csv(path, index=False)
    merge_prices = lambda x: (x * raw_prices.loc[x.index, 'Volume']).sum() / raw_prices.loc[x.index, 'Volume'].sum() if raw_prices.loc[x.index, 'Volume'].sum() != 0 else 0
    # Merge the prices of the two market indices (APX MIDP and APX SPOT) into a single price column
    prices = raw_prices.groupby('StartTime').agg({'Price': merge_prices, "SettlementDate": "first"}).reset_index()
    prices['DATETIME'] = pd.to_datetime(prices['StartTime'])
    prices.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'market-prices.csv'), index=False)

    return prices

def fetch_data(skip_generation=False, skip_prices=False):
    # Load data from CSV files
    generation = fetch_generation() if not skip_generation else pd.read_csv(os.path.join(RAW_DATA_DIR, 'generation.csv'), index_col='DATETIME', parse_dates=True)
    prices = fetch_prices() if not skip_prices else pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'market-prices.csv'), index_col='DATETIME', parse_dates=True)
    
    print(f'[DEBUG] Loaded {len(generation)} generation records and {len(prices)} price records')
    
    merged = pd.merge(prices, generation, on='DATETIME', how='inner')
    # Rename columns to match expected format
    merged = merged.rename(columns={'GENERATION': 'Total'})
    merged['SettlementDate'] = pd.to_datetime(merged['SettlementDate'])    

    # Drop rows where there is not 48 settlement periods in a day (i.e. incomplete days)
    merged = merged.groupby('SettlementDate').filter(lambda x: len(x) == 48)

    # Define aggregation functions for each column
    aggregation_functions = dict.fromkeys([col for col in NESO_GENERATION_TYPES.keys()] + ['Total'], 'sum')
    # Calculate weighted average price dividing sum of 'Wholesale Price' by sum of 'Total'
    aggregation_functions['Price'] = lambda x: np.average(values=merged['Price'], weights=merged['Total'])
    # Group by date and calculate average price and generation for the target generation type
    daily_data = merged.groupby(merged['SettlementDate']).agg(aggregation_functions).reset_index()
    for gen_type in NESO_GENERATION_TYPES.keys():
        daily_data[gen_type + '_perc'] = (daily_data[gen_type] / daily_data['Total']) * 100
    daily_data = daily_data.sort_values(by='SettlementDate').reset_index(drop=True)

    # save the cleaned data to a new CSV file
    daily_data.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'daily_data.csv'), index=False)
    merged.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'half_hourly_data.csv'), index=False)

def merge_generators() :
    print('Merging generator data from various sources...')
    def convert_coordinates(row):
        if pd.notna(row['X-coordinate']) and pd.notna(row['Y-coordinate']):
            return OSGridReference(int(float(row['X-coordinate'])), int(float(row['Y-coordinate']))).toLatLong()
        return OSGridReference(0, 0).toLatLong()  # Return None for both latitude and longitude if coordinates are missing

    # Load generator data from CSV files
    print('Loading generator data from CSV files...')
    misc_generators = pd.read_csv(os.path.join(MANUAL_DATA_DIR, 'generators.csv'))
    misc_generators = misc_generators[['Ref ID', 'Site Name', 'Latitude', 'Longitude']]
    renewable_generators = pd.read_csv(os.path.join(RAW_DATA_DIR, 'repd.csv')).assign(
        latlong=lambda x: x.apply(lambda row: convert_coordinates(row), axis=1),
        Latitude=lambda x: x['latlong'].apply(lambda ll: ll.latitude if ll else None),
        Longitude=lambda x: x['latlong'].apply(lambda ll: ll.longitude if ll else None)
    )
    renewable_generators = renewable_generators[['Ref ID', 'Site Name', 'Latitude', 'Longitude']]

    all_generators = pd.concat([misc_generators, renewable_generators])
    all_generators.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'all_generators.csv'), index=False)

    print('Loading BMU data from CSV files...')
    output_generators = pd.DataFrame(columns=['Ref ID', 'Site Name', 'Latitude', 'Longitude', 'BMU IDs'])
    bmus = pd.read_csv(os.path.join(MANUAL_DATA_DIR, 'bmus.csv'))
    bmus = bmus[['elexonBmUnit', 'Ref ID', 'fuelType', 'demandCapacity', 'generationCapacity', 'gspGroupName', 'interconnectorId']]

    # For each interconnector use the interconnectorId to find all BMUs associated with it and add the corresponding ref ID to each BMU
    interconnector_bmus = bmus[bmus['elexonBmUnit'].str.startswith('I_')]
    for interconnector_id in interconnector_bmus['interconnectorId'] :
        associated_bmus = bmus[bmus['interconnectorId'] == interconnector_id]
        # Get the first Ref ID associated with this interconnector
        ref_id = associated_bmus['Ref ID'].iloc[0]
        bmus.loc[bmus['interconnectorId'] == interconnector_id, 'Ref ID'] = ref_id

    print('Merging generator data with BMU data...')
    bmu_data = pd.merge(all_generators, bmus, on='Ref ID', how='inner')
    bmu_data = bmu_data.groupby('Ref ID').agg({
        'Site Name': 'first',
        'Latitude': 'first',
        'Longitude': 'first',
        'fuelType': 'first',
        'elexonBmUnit': list
    })
    # Remove all text after a dash or in parentheses in the 'Site Name' column
    bmu_data['Site Name'] = bmu_data['Site Name'].str.replace(r'[-(].*', '', regex=True).str.strip()
    
    bmu_data.to_json(os.path.join(TRANSFORMED_DATA_DIR, 'all_generators.json'), orient='records', indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and process electricity market data")
    parser.add_argument('--skip-generation', action='store_true', help='Skip fetching generation data')
    parser.add_argument('--skip-prices', action='store_true', help='Skip fetching price data')
    parser.add_argument('--update-generators', action='store_true', help='Update list of generators')
    args = parser.parse_args()

    if not args.skip_generation or not args.skip_prices:
        fetch_data(args.skip_generation, args.skip_prices)
    if args.update_generators :
        merge_generators()
    fetch_embedded_generation()
    fetch_gas_prices()
