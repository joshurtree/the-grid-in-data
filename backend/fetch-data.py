#Fetches and cleans the data from the GB electricity market, returning a DataFrame with the relevant columns.
import argparse
from datetime import date, datetime, timezone, timedelta
from io import StringIO
import os
from OSGridConverter import grid2latlong, OSGridReference
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm
from bmrs import fetch_FPN, fetch_extended_bmrs_data, fetch_bmrs_data
from neso import fetch_embedded_generation
from io import BytesIO
from constants import MANUAL_DATA_DIR, NESO_GENERATION_TYPES, RAW_DATA_DIR, TRANSFORMED_DATA_DIR

system_prices = [
    ('systemaveragepricesapofgas', 'systemaveragepriceofgas', '1.Daily SAP Gas', 'system_gas'), 
    ('systempriceofelectricity', 'electricityprices', '1.Daily SP Electricity', 'system_electricity')
]

def fetch_system_prices() :
    print('Fetching system prices from ONS...')
    # System prices are published on Thursday
    date = datetime.now() - timedelta(days=1)
    date = date - timedelta(days=(date.weekday() - 3) % 7)

    for dataset in system_prices:
        uri = f"/economy/economicoutputandproductivity/output/datasets/{dataset[0]}/{date.year}/{dataset[1]}dataset{date.strftime('%d%m%y')}.xlsx"
        response = requests.get(f"https://www.ons.gov.uk/file?uri={uri}")
        response.raise_for_status()

        prices = pd.read_excel(BytesIO(response.content), dataset[2], skiprows=4)
        prices['Date'] = pd.to_datetime(prices['Date'])
        prices.rename(columns={prices.columns[1]: 'Price'}, inplace=True)        
        prices['Price'] = pd.to_numeric(prices['Price'], errors='coerce')
        prices.to_csv(os.path.join(RAW_DATA_DIR, f"{dataset[3]}_prices.csv"), index=False)

def fetch_embedded_generation():
    # Load data from CSV files
    print('Fetching embedded generation data from Neso API...')
    embedded_generation = pd.DataFrame()
    path = os.path.join(RAW_DATA_DIR, 'embedded_generation.csv')
    if os.path.exists(path) :
        embedded_generation = pd.read_csv(path)

    additional = pd.read_csv('https://api.neso.energy/dataset/91c0c70e-0ef5-4116-b6fa-7ad084b5e0e8/resource/db6c038f-98af-4570-ab60-24d71ebd0ae5/download/202607090125_embedded_forecast.csv')
    additional['EMBEDDED_FORECAST_TOTAL'] = additional['EMBEDDED_WIND_FORECAST'] + additional['EMBEDDED_SOLAR_FORECAST']
    additional.drop(columns=['DATE_GMT', 'TIME_GMT'], inplace=True)
    embedded_generation = pd.concat([embedded_generation, additional], ignore_index=True)
    embedded_generation.to_csv(os.path.join(RAW_DATA_DIR, 'embedded_generation.csv'), index=False)

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
        start_date = date.fromisoformat(raw_prices['StartTime'].max()[:10])

    # Fetch additional prices from Elexon API if needed
    additional_prices = fetch_extended_bmrs_data(
        lambda s, f: fetch_bmrs_data("balancing/pricing/market-index", params={'from': s, 'to': f}), 
        start_date, 
        "Fetching market prices"
    )
    raw_prices = pd.concat([raw_prices, additional_prices], ignore_index=True)

    print("Merging market prices...")
    merge_prices = lambda x: (x * raw_prices.loc[x.index, 'Volume']).sum() / raw_prices.loc[x.index, 'Volume'].sum() if raw_prices.loc[x.index, 'Volume'].sum() != 0 else 0
    # Merge the prices of the two market indices (APX MIDP and APX SPOT) into a single price column
    prices = raw_prices.groupby('StartTime').agg({'Price': merge_prices, "SettlementDate": "first"}).reset_index()
    prices['DATETIME'] = pd.to_datetime(prices['StartTime'])
    prices.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'market-prices.csv'), index=False)

    return prices

def fetch_demand():
    print('Fetching demand data from Elexon API...')
    demand = pd.DataFrame()
    path = os.path.join(RAW_DATA_DIR, 'demand.csv')
    start_date = date(2017, 1, 1)

    if os.path.exists(path) :
        # Load data from CSV files
        demand = pd.read_csv(path)
        start_date = date.fromisoformat(demand['settlementDate'].max())

    additional_demand = fetch_extended_bmrs_data(lambda s, f: fetch_bmrs_data("demand/outturn", params={'from': s, 'to': f}), start_date, "Fetching demand data")
    demand = pd.concat([demand, additional_demand], ignore_index=True)
    demand.to_csv(os.path.join(RAW_DATA_DIR, 'demand.csv'), index=False)

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
    parser.add_argument('--skip-demand', action='store_true', help='Skip fetching demand data')
    parser.add_argument('--skip-embedded-generation', action='store_true', help='Skip fetching embedded generation data')
    parser.add_argument('--skip-system-prices', action='store_true', help='Skip fetching system prices data')
    args = parser.parse_args()

    # Load data from CSV files
    generation = fetch_generation() if not args.skip_generation else pd.read_csv(os.path.join(RAW_DATA_DIR, 'generation.csv'), index_col='DATETIME', parse_dates=True)
    prices = fetch_prices() if not args.skip_prices else pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'market-prices.csv'), index_col='DATETIME', parse_dates=True)

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
    aggregation_functions['Price'] = lambda x: np.average(merged['Price'], weights=merged['Total'])
    # Group by date and calculate average price and generation for the target generation type
    daily_data = merged.groupby(merged['SettlementDate']).agg(aggregation_functions).reset_index()
    for gen_type in NESO_GENERATION_TYPES.keys():
        daily_data[gen_type + '_perc'] = (daily_data[gen_type] / daily_data['Total']) * 100
    daily_data = daily_data.sort_values(by='SettlementDate').reset_index(drop=True)

    # save the cleaned data to a new CSV file
    daily_data.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'daily_data.csv'), index=False)
    merged.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'half_hourly_data.csv'), index=False)

    if not args.skip_demand:
        fetch_demand()
    if not args.skip_embedded_generation:
        fetch_embedded_generation()
    if not args.skip_system_prices:
        fetch_system_prices()
