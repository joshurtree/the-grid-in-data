from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO
import pandas as pd
from titlecase import titlecase
import numpy as np

from backend import fetch_from_url

from .bmrs import fetch_extended_bmrs_data, fetch_bmrs_data
from .helpers import camel_case_to_capitalised, snake_case_to_capitalised
from .ckan import CKANClient, Package, Endpoint
from constants import DATETIME_FIELD, DATE_FIELD, NESO_GENERATION_TYPES
from datasources.system import *
from datasources.supply import capacity_factors_dataset

neso_client = CKANClient(base_url="https://api.neso.energy")
    
BALANCING_MECHANISM = Package("daily-balancing-costs-balancing-services-use-of-system", neso_client)
DEMAND = Package('historic-demand-data', neso_client)
GENERATION = Endpoint("f93d1835-75bc-43e5-84ad-12472b180a98", neso_client)
EMBEDDED_FORECAST = Endpoint("db6c038f-98af-4570-ab60-24d71ebd0ae5", neso_client)
DEMAND_FORECAST = Endpoint("f93d1835-75bc-43e5-84ad-12472b180a98", neso_client)
PRICES = Endpoint("4f27eea5-7038-4f73-9740-e3e4ad47c26a", neso_client)

def to_local_datetime(date: str) -> datetime:
    """
    Convert a datetime string to a timezone-aware datetime object in utc timezone.
    """
    dt = datetime.fromisoformat(date)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=0)))
    return dt


def to_datetime(date: pd.Series[str], settlement_period: pd.Series[int]) -> pd.DatetimeIndex:
    """
    Convert a date and settlement period to a datetime object.
    Settlement periods are 30-minute intervals starting from 00:00.
    """
    def convert_row(row) -> datetime:
        # Calculate the hour and minute based on the settlement period
        settlement_period = row[1]
        hour = (settlement_period - 1) // 2
        minute = 30 if settlement_period % 2 == 0 else 0
        is_dst = False

        # Detect if last Sunday of March or October and adjust for BST/GMT
        date_obj = pd.to_datetime(row[0], format="mixed", errors='coerce')
        if (date_obj.month in [3, 10] and date_obj.weekday() == 6 and date_obj.day + 7 > 31):
            # Last Sunday of March or October and after 01:00, adjust for BST/GMT
            if date_obj.month == 3 and hour >= 1:
                # BST starts, add 1 hour
                hour += 1
            elif date_obj.month == 10:
                if hour > 1:
                    # BST ends, subtract 1 hour
                    hour -= 1

        # Create a datetime object from the date string and calculated hour and minute (fixed to GMT timezone)
        return date_obj.replace(hour=hour, minute=minute).tz_localize('utc')

    return pd.to_datetime([convert_row(row) for row in zip(date, settlement_period)], errors='coerce')

def fetch_generation() -> None:    
    print('Fetching generation data from Neso API...')
    #generation = generation_source.load_data() if generation_source.exists() else pd.DataFrame()
    #print(f'[DEBUG] Loaded {len(generation)} generation records')
    generation = GENERATION()
    generation[DATETIME_FIELD] = pd.to_datetime(generation['DATETIME']).dt.tz_localize('utc')
    generation = (generation
        .drop(columns=['DATETIME'])
        .rename(columns={'WIND_EMB': 'Embedded Wind'})
        .rename(columns=dict(zip(generation.columns, [titlecase(col.replace('_', ' ').replace('perc', '(%)')) for col in generation.columns])))
    )

    generation_source.save_data(generation)

def fetch_prices():
    print('Fetching market prices from Neso API...')
    raw_prices = pd.DataFrame()
    
    if wholesale_price_source.exists():
        # Load data from CSV files
        raw_prices = wholesale_price_source.load_data()
        start_date = raw_prices['Settlement Date'].max()
    else:
        start_date = datetime(2017, 1, 1, tzinfo=timezone.utc)
    
    additional_prices = fetch_extended_bmrs_data(
        "balancing/pricing/market-index", 
        start_date,
        "Fetching market prices"
    )

    if not additional_prices.empty:
        def merge_prices(x):
            series = pd.to_numeric(additional_prices.loc[x.index, 'volume'], errors='coerce')
            # Ensure series is a pandas Series aligned with the group's index so .sum() is always available
            series = pd.Series(series, index=x.index)
            series_sum = series.sum()
            if series_sum == 0 or np.isnan(series_sum):
                return 0.0
            return (x * series).sum() / series_sum

        # Merge the prices of the two market indices (APX MIDP and APX SPOT) into a single price column
        additional_prices = camel_case_to_capitalised(
            additional_prices
            .groupby('startTime')
            .agg({'price': merge_prices, "settlementDate": "first"})
            .reset_index()
        )

        additional_prices[DATETIME_FIELD] = pd.to_datetime(additional_prices['Start Time']).dt.tz_convert('utc')
        additional_prices.drop(columns='Start Time', inplace=True)
        additional_prices['Settlement Date'] = pd.to_datetime(additional_prices['Settlement Date'])
        raw_prices = pd.concat([raw_prices, additional_prices], ignore_index=True)
        wholesale_price_source.save_data(raw_prices)

def fetch_demand(process_only: bool) -> None:
    if process_only:
        return
    print('Fetching demand data from Neso API...')

    demand = DEMAND()
    demand.rename(
        columns={
            'SETTLEMENT_DATE': DATE_FIELD,
            'ND': 'National Demand',
            'TSD': 'Transmission System Demand'
        }, inplace=True)
    demand = snake_case_to_capitalised(demand, ['IFA', 'IFA2', 'BM'])

    demand[DATETIME_FIELD] = to_datetime(demand[DATE_FIELD], demand['Settlement Period'])
    for col in demand.columns:
        if col not in [DATETIME_FIELD, DATE_FIELD, 'Settlement Period', 'Forecast Actual Indicator', 'Id']:
            # coerce columns to numeric, replacing non-numeric values with NaN
            demand[col] = pd.to_numeric(demand[col], errors='coerce').replace({np.nan: 0})
            #demand[col + ' (MWh)'] = demand[col] / 2  # Convert MW to MWh for the half-hourly period
    
    interconnectors = [col for col in demand.columns if col.endswith('Flow')]
    demand['Net Imports'] = pd.to_numeric(demand[interconnectors].sum(axis=1), errors='coerce')
    demand['Net Imports (%)'] = (demand['Net Imports'] / demand['Transmission System Demand']) * 100

    # Determine station load based on whether the timestamp is in daylight saving time (BST).
    # For GMT (no DST) use 600, for BST (DST) use 500.
    def is_dst(ts):
        try:
            return bool(ts.dst() != pd.Timedelta(0))
        except Exception:
            return False

    demand['Station Load'] = demand[DATETIME_FIELD].apply(lambda ts: 500 if is_dst(ts) else 600)
    # Calculate gross exports as the sum of all interconnector flows that are negative (i.e., exports)
    demand['Exports'] = demand[interconnectors].apply(lambda x: np.sum(x[x < 0]), axis=1)
    demand['Imports'] = demand[interconnectors].apply(lambda x: np.sum(x[x > 0]), axis=1)
    
    # Calculate station load as the difference between Transmission System Demand and the sum National Demand, Pump Storage Pumping, and Exports
    demand['Transmission Losses'] = demand['Transmission System Demand']
    demand['Transmission Losses'] -= demand['National Demand']
    demand['Transmission Losses'] -= demand['Pump Storage Pumping']
    demand['Transmission Losses'] -= demand['Station Load']
    demand['Transmission Losses'] += demand['Exports']
    
    # If Transmission Losses is negative, set it to a tenth of National Demand (this is a fallback for data issues)
    demand['Transmission Losses'] = demand.apply(lambda row: row['Transmission Losses'] if row['Transmission Losses'] > 0 else row['National Demand'] / 10, axis=1)

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
    bm_data = bm_payments_source.load_data() if bm_payments_source.exists() else pd.DataFrame()
    new_bm_data = BALANCING_MECHANISM()
    new_bm_data = new_bm_data.groupby('SETT_DATE').agg({
        'Energy Imbalance': 'sum',
        'Frequency Control': 'sum',
        'Positive Reserve': 'sum',
        'Constraints': 'sum',
        'Negative Reserve': 'sum',
        'Other': 'sum'
    }).reset_index()
    new_bm_data = new_bm_data.rename(columns={'SETT_DATE': DATE_FIELD})
    new_bm_data[DATE_FIELD] = pd.to_datetime(new_bm_data[DATE_FIELD], format="mixed", dayfirst=True, errors='coerce')
    print(f'[DEBUG] Fetched {len(new_bm_data)} balancing mechanism records')
    bm_payments_source.save_data(pd.concat([bm_data, new_bm_data], ignore_index=True))

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
    merged.rename(columns={'Settlement Date': DATE_FIELD}, inplace=True)
      
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
    daily_data = merged.groupby(DATE_FIELD).agg(agg_map).reset_index()
    for gen_type in NESO_GENERATION_TYPES.values():
        if gen_type in daily_data.columns:
            daily_data[gen_type + ' (%)'] = (daily_data[gen_type] / daily_data['Total']) * 100

    # save the cleaned data to a new CSV file
    half_hourly_dataset.save_data(merged)
    daily_dataset.save_data(daily_data)

def create_elec_vs_gas_dataset():
    print('Creating electricity vs gas dataset...')
    wholesale_prices, gas_prices = gasvselec_dataset.base_data()
    merged = (
        pd.merge(wholesale_prices, gas_prices, on=DATE_FIELD, how='inner')
        .rename(columns={'Price_x': 'Electricity Price', 'Price_y': 'Gas Price'})
    )

    merged['Ratio'] = merged['Electricity Price'] / merged['Gas Price']
    gasvselec_dataset.save_data(merged)

def create_supply_vs_demand_dataset():
    print('Creating supply vs demand dataset...')
    generation, demand = supply_vs_demand_dataset.base_data()
    generation.drop(columns=['Imports'], inplace=True)
    merged = pd.merge(generation, demand, on=DATETIME_FIELD, how='inner')

    # Invert demand values to make them negative for plotting purposes
    merged['National Demand'] = -merged['National Demand']
    merged['Storage Load'] = -merged['Pump Storage Pumping']
    merged['Station Load'] = -merged['Station Load']
    merged['Transmission Losses'] = -merged['Transmission Losses']
    merged['Transmission System Demand'] = -merged['Transmission System Demand']
    #merged.rename(columns={'Embedded Wind Generation': 'Embedded Wind', 'Embedded Solar Generation': 'Embedded Solar'}, inplace=True)
    drop_columns = [
        #'Transmission System Demand', 
        'Net Imports', 
        'England Wales Demand', 
        'Scottish Transfer', 
        'Date', 
        'Settlement Period', 
        'Forecast Actual Indicator', 
        'Pump Storage Pumping', 
        'Embedded Wind Generation', 
        'Embedded Solar Generation'
    ]
    drop_columns += ['Low Carbon', 'Renewable', 'Fossil', 'Zero Carbon']
    drop_columns += [col for col in merged.columns if col.endswith('Flow')]
    drop_columns += [col for col in merged.columns if col.endswith('(MWh)')]
    drop_columns += [col for col in merged.columns if col.endswith(' (%)')]
    drop_columns += [col for col in merged.columns if col.endswith('Capacity')]
    merged.drop(columns=drop_columns, inplace=True)

    supply_vs_demand_dataset.save_data(merged)

def create_generation_datasets(process_only: bool):
    create_elec_vs_gas_dataset()
    create_supply_vs_demand_dataset()
