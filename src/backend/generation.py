from datetime import date
import pandas as pd
from titlecase import titlecase
import numpy as np

from .bmrs import fetch_extended_bmrs_data, fetch_bmrs_data
from .helpers import camel_case_to_capitalised
from .ckan import CKANClient, Package, Endpoint
from constants import DATETIME_FIELD, DATE_FIELD, NESO_GENERATION_TYPES
from datasources.system import generation_source, wholesale_price_source, demand_source, bm_payments_source, half_hourly_dataset, daily_dataset, gasvselec_dataset
from datasources.supply import capacity_factors_dataset

neso_client = CKANClient(base_url="https://api.neso.energy")
    
BALANCING_MECHANISM = Package("daily-balancing-costs-balancing-services-use-of-system", neso_client)
DEMAND = Endpoint("8a4a771c-3929-4e56-93ad-cdf13219dea5", neso_client)
GENERATION = Endpoint("f93d1835-75bc-43e5-84ad-12472b180a98", neso_client)
EMBEDDED_FORECAST = Endpoint("db6c038f-98af-4570-ab60-24d71ebd0ae5", neso_client)
DEMAND_FORECAST = Endpoint("f93d1835-75bc-43e5-84ad-12472b180a98", neso_client)

def fetch_generation() -> None:
    def process_generation_data(additional: pd.DataFrame) -> pd.DataFrame:
        additional[DATETIME_FIELD] = pd.to_datetime(additional['DATETIME'])
        additional = (additional
            .drop(columns=['DATETIME'])
            .rename(columns={'WIND_EMB': 'Embedded Wind'})
            .rename(columns=dict(zip(additional.columns, [titlecase(col.replace('_', ' ').replace('perc', '(%)')) for col in additional.columns])))
        )
        return additional
    
    print('Fetching generation data from Neso API...')
    generation = generation_source.load_data() if generation_source.exists() else pd.DataFrame()
    print(f'[DEBUG] Loaded {len(generation)} generation records')
    additional = GENERATION(offset=len(generation), sort='DATETIME asc')

    if not additional.empty:    
        generation = pd.concat([generation, process_generation_data(additional)], ignore_index=True)
    
    generation_source.save_data(generation)

def fetch_prices():
    print('Fetching market prices from Elexon API...')
    raw_prices = pd.DataFrame()
    
    if wholesale_price_source.exists():
        # Load data from CSV files
        raw_prices = wholesale_price_source.load_data()
        start_date = raw_prices['Settlement Date'].max()
    else:
        start_date = date(2017, 1, 1)
    
    additional_prices = fetch_extended_bmrs_data(
        lambda s, f: fetch_bmrs_data("balancing/pricing/market-index", params={'from': s, 'to': f}), 
        start_date,
        "Fetching market prices"
    )

    if not additional_prices.empty:
        def merge_prices(x):
            series = pd.to_numeric(additional_prices.loc[x.index, 'volume'], errors='coerce')
            return (x * series).sum() / series.sum() if series.sum() != 0 else 0

        # Merge the prices of the two market indices (APX MIDP and APX SPOT) into a single price column
        additional_prices = camel_case_to_capitalised(
            additional_prices
            .groupby('startTime')
            .agg({'price': merge_prices, "settlementDate": "first"})
            .reset_index()
        )

        additional_prices[DATETIME_FIELD] = pd.to_datetime(additional_prices['Start Time'])
        additional_prices.drop(columns='Start Time', inplace=True)
        additional_prices['Settlement Date'] = pd.to_datetime(additional_prices['Settlement Date'])
        raw_prices = pd.concat([raw_prices, additional_prices], ignore_index=True)
        wholesale_price_source.save_data(raw_prices)

def fetch_demand(process_only: bool) -> None:
    if process_only:
        return
    print('Fetching demand data from Elexon API...')
    demand = pd.DataFrame()
    start_date = date(2017, 1, 1)

    if demand_source.exists() :
        # Load data from CSV files
        demand = demand_source.load_data()
        start_date = demand['settlementDate'].max()

    additional_demand = fetch_extended_bmrs_data(lambda s, f: fetch_bmrs_data("demand/outturn", params={'from': s, 'to': f}), start_date, "Fetching demand data")
    additional_demand = camel_case_to_capitalised(additional_demand)
    additional_demand[DATETIME_FIELD] = pd.to_datetime(additional_demand['Start Time'])
    additional_demand.drop(columns='Start Time', inplace=True)
    additional_demand['Settlement Date'] = pd.to_datetime(additional_demand['Settlement Date'])
    additional_demand['Publish Time'] = pd.to_datetime(additional_demand['Publish Time'])

    demand = pd.concat([demand, additional_demand], ignore_index=True)
    demand_source.save_data(demand)

def merge_generators(process_only: bool) -> None:
    if process_only:
        return
    # print('Merging generator data from various sources...')
    # def convert_coordinates(row):
    #     if pd.notna(row['X-coordinate']) and pd.notna(row['Y-coordinate']):
    #         return OSGridReference(int(float(row['X-coordinate'])), int(float(row['Y-coordinate']))).toLatLong()
    #     return OSGridReference(0, 0).toLatLong()  # Return None for both latitude and longitude if coordinates are missing
    
    # generators = pd.read_excel(os.path.join(MANUAL_DATA_PATH, 'generators.ods'), sheet='Generators', engine='odf')


    # # Load generator data from CSV files
    # print('Loading generator data from CSV files...')
    # misc_generators, renewable_generators, bmus = generators_dataset.base_data()
    # misc_generators = misc_generators[['Ref ID', 'Site Name', 'Latitude', 'Longitude']]
    # renewable_generators = renewable_generators.assign(
    #     latlong=lambda x: x.apply(lambda row: convert_coordinates(row), axis=1),
    #     Latitude=lambda x: x['latlong'].apply(lambda ll: ll.latitude if ll else None),
    #     Longitude=lambda x: x['latlong'].apply(lambda ll: ll.longitude if ll else None)
    # )
    # renewable_generators = renewable_generators[['Ref ID', 'Site Name', 'Latitude', 'Longitude']]

    # all_generators = pd.concat([misc_generators, renewable_generators])
    
    # print('Loading BMU data from CSV files...')
    # output_generators = pd.DataFrame(columns=['Ref ID', 'Site Name', 'Latitude', 'Longitude', 'BMU IDs'])
    # bmus = bmus[['elexonBmUnit', 'Ref ID', 'fuelType', 'demandCapacity', 'generationCapacity', 'gspGroupName', 'interconnectorId']]

    # # For each interconnector use the interconnectorId to find all BMUs associated with it and add the corresponding ref ID to each BMU
    # interconnector_bmus = bmus[bmus['elexonBmUnit'].str.startswith('I_')]
    # for interconnector_id in interconnector_bmus['interconnectorId'] :
    #     associated_bmus = bmus[bmus['interconnectorId'] == interconnector_id]
    #     # Get the first Ref ID associated with this interconnector
    #     ref_id = associated_bmus['Ref ID'].iloc[0]
    #     bmus.loc[bmus['interconnectorId'] == interconnector_id, 'Ref ID'] = ref_id

    # print('Merging generator data with BMU data...')
    # bmu_data = pd.merge(all_generators, bmus, on='Ref ID', how='inner')
    # bmu_data = bmu_data.groupby('Ref ID').agg({
    #     'Site Name': 'first',
    #     'Latitude': 'first',
    #     'Longitude': 'first',
    #     'fuelType': 'first',
    #     'elexonBmUnit': list
    # })
    # # Remove all text after a dash or in parentheses in the 'Site Name' column
    # bmu_data['Site Name'] = bmu_data['Site Name'].str.replace(r'[-(].*', '', regex=True).str.strip()

    # generators_dataset.save_data(bmu_data)

def fetch_balancing_mechanism_data(process_only: bool) -> None:
    if process_only:
        return
    print('Fetching balancing mechanism data from Neso API...')
    bm_data = BALANCING_MECHANISM()
    bm_data = bm_data.groupby('SETT_DATE').agg({
        'Energy Imbalance': 'sum',
        'Frequency Control': 'sum',
        'Positive Reserve': 'sum',
        'Constraints': 'sum',
        'Negative Reserve': 'sum',
        'Other': 'sum'
    }).reset_index()
    bm_data = bm_data.rename(columns={'SETT_DATE': DATE_FIELD})
    bm_data[DATE_FIELD] = pd.to_datetime(bm_data[DATE_FIELD], format="mixed", dayfirst=True, errors='coerce')
    print(f'[DEBUG] Fetched {len(bm_data)} balancing mechanism records')
    bm_payments_source.save_data(bm_data)

def fetch_generation_and_prices(process_only: bool):
    if not process_only:
        fetch_generation()
        fetch_prices()
    
    # Load data from CSV files
    generation, prices = half_hourly_dataset.base_data()
    print(f'[DEBUG] Loaded {len(generation)} generation records and {len(prices)} price records')

    merged = pd.merge(generation, prices, on=DATETIME_FIELD, how='inner')
    # Rename columns to match expected format
    merged = merged.rename(columns={'Generation': 'Total'})
      
    # We need a weighted average for Price using Total as weights. When using groupby.agg,
    # the aggregation function for a column receives a Series for that column. We can
    # access the corresponding 'Total' values using the Series' index into `merged`.
    def weighted_price(s: pd.Series) -> float:
        # s is the 'Price' series for the group; look up matching 'Total' via original index
        try:
            weights = merged.loc[s.index, 'Total']
            # if weights sum to zero fall back to simple mean (or 0 if empty)
            if weights.sum() == 0:
                return float(s.mean()) if len(s) > 0 else 0.0
            return float(np.average(s, weights=weights))
        except Exception:
            # If anything goes wrong, return simple mean or 0
            return float(s.mean()) if len(s) > 0 else 0.0

    # Define aggregation functions for each column: sum for generation columns and total
    to_generation = lambda x: x.sum()/2  # Half the generation values to convert from MW to MWh for the half-hourly period
    aggregation_functions = [(col, to_generation) for col in list(NESO_GENERATION_TYPES.values()) + ['Total']]    
    agg_map = dict(aggregation_functions + [('Price', weighted_price)])

    # Group by date and calculate aggregated sums + weighted price
    daily_data = merged.groupby('Settlement Date').agg(agg_map).reset_index()
    for gen_type in NESO_GENERATION_TYPES.values():
        if gen_type in daily_data.columns:
            daily_data[gen_type + ' (%)'] = (daily_data[gen_type] / daily_data['Total']) * 100

    # save the cleaned data to a new CSV file
    half_hourly_dataset.save_data(merged)
    daily_dataset.save_data(daily_data)

def create_elec_vs_gas_dataset(process_only: bool):
    print('Creating electricity vs gas dataset...')
    wholesale_prices, gas_prices = gasvselec_dataset.base_data()
    merged = (
        pd.merge(wholesale_prices, gas_prices, left_on="Settlement Date", right_on=DATE_FIELD, how='inner')
        .rename(columns={'Price_x': 'Electricity Price', 'Price_y': 'Gas Price'})
        .drop(columns='Settlement Date')
    )

    merged['Ratio'] = merged['Electricity Price'] / merged['Gas Price']
    gasvselec_dataset.save_data(merged)

def calculate_capacity_factors():
    """
    Calculates the capacity factors for wind and solar based on generation and capacity data.
    For each quarter it calculates the average, minimum, and maximum capacity factors for daily, weekly, and monthly periods.
    """

    print("Calculating capacity factors...")
    capacity_factors, generation = capacity_factors_dataset.base_data()
    capacity_factors['Wind Capacity (MW)'] = capacity_factors['Onshore Wind Capacity (MW)'] + capacity_factors['Offshore Wind Capacity (MW)']
    generation = generation.rename(columns={'Settlement Date': DATE_FIELD})
    generation['Wind'] = generation['Wind'] + generation['Embedded Wind']

    # Interpolate capacity factors for missing dates
    capacity_factors = (
        capacity_factors
        .set_index(DATE_FIELD).reindex(pd.date_range(start=capacity_factors[DATE_FIELD].min(), end=capacity_factors[DATE_FIELD].max(), freq='D'))
        .interpolate(method='time').reset_index().rename(columns={'index': DATE_FIELD})
    )
    merged = pd.merge(generation, capacity_factors, on=DATE_FIELD, how='left', suffixes=('', '_capacity'))
    columns_to_drop = [col for col in merged.columns if col not in {DATE_FIELD, 'Wind Capacity (MW)', 'Solar Capacity (MW)'}]
    for window in [('Daily', 1), ('Weekly', 7), ('Monthly', 30), ('Quarterly', 90)]:
        for gen_type in ['Wind', 'Solar']:
            merged[f'{gen_type} Capacity Factor ({window[0]})'] = merged[gen_type].rolling(window=window[1]).sum() / (merged[f'{gen_type} Capacity (MW)'].rolling(window=window[1]).sum() * 24) * 100

    merged = merged.drop(columns=columns_to_drop)
    capacity_factors_dataset.save_data(merged)
