#Fetches and cleans the data from the GB electricity market, returning a DataFrame with the relevant columns.
from bs4 import BeautifulSoup
from collections.abc import Callable
from datetime import date, datetime, timezone, timedelta
from io import StringIO,BytesIO
import numpy as np
import os
from OSGridConverter import grid2latlong, OSGridReference
import pandas as pd
import random
import re
import requests
import sys
from functools import partial
from titlecase import titlecase
from tqdm import tqdm

from backend.bmrs import fetch_FPN, fetch_extended_bmrs_data, fetch_bmrs_data
import backend.neso as neso
from backend.metric import Metric
from backend.constants import INFLATORS, MANUAL_DATA_PATH, NESO_GENERATION_TYPES, RAW_DATA_PATH, PROCESSED_DATA_PATH, DATE_FIELD, DATETIME_FIELD
from datasources.supply import *
from datasources.policy import *
from datasources.system import *

http_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Converts dataframe columns from using camel case to capitised words
def camel_case_to_capitalised(df: pd.DataFrame) :
    rename = dict(zip(df.columns, [titlecase(re.sub("([a-z])([A-Z])", r"\1 \2", col)) for col in df.columns]))
    return df.rename(columns=rename)

def snake_case_to_capitalised(df: pd.DataFrame) :
    return df.rename(columns=dict(zip(df.columns, [titlecase(re.sub("_", " ", col)) for col in df.columns])))

def fix_units(df: pd.DataFrame) -> pd.DataFrame:
    def do_fix(col: str) -> str:
        for match in [('GBP Per MWh', '£/MWh'), ('MWh', 'MWh'), ('MW', 'MW'), ('GBP', '£'), ('CO2e', 'CO2e')]:
            if match[0] in col:
                return col.replace(match[0], f'({match[1]})')
        return col

    return df.rename(columns={col: do_fix(col) for col in df.columns})

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
            ons_prices.rename(columns={'SAP actual day': 'Price'}, inplace=True)
            ons_prices["Price"] = ons_prices["Price"] * 10

            ons_system_gas_price_source.save_data(ons_prices)
    except Exception as e:
        print(f"Error fetching ONS gas prices: {e}")
        ons_prices = ons_system_gas_price_source.load_data()

    gas_prices = pd.DataFrame()
    if ngas_system_gas_price_source.exists():
        gas_prices = ngas_system_gas_price_source.load_data()
    startDate = (gas_prices[DATE_FIELD].max() + timedelta(days=1)).strftime('%Y-%m-%d') if not gas_prices.empty else '2017-01-01'
    endDate = datetime.now().strftime('%Y-%m-%d')
    fetch_url = f"https://data.nationalgas.com/api/find-gas-data-download?applicableFor=Y&dateFrom={startDate}&dateTo={endDate}&dateType=GASDAY&latestFlag=N&ids=PUBOB603&type=CSV"
    try:
        response = requests.get(fetch_url, headers=http_headers)
        response.raise_for_status()
        gas_prices = pd.read_csv(BytesIO(response.content))
        gas_prices.drop(columns=['Applicable At', 'Data Item', 'Generated Time', 'Quality Indicator'], inplace=True)
        gas_prices.rename(columns={'Applicable For': DATE_FIELD, 'Value': 'Price'}, inplace=True)
        gas_prices[DATE_FIELD] = pd.to_datetime(gas_prices[DATE_FIELD], format='%d/%m/%Y')
        gas_prices["Price"] = gas_prices["Price"] * 10
        ngas_system_gas_price_source.save_data(gas_prices)
    except Exception as e:
        print(f"Error fetching National Gas prices: {e}")

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
    past_gas_prices = past_gas_prices.set_index(DATE_FIELD).resample('MS').mean().reset_index()

    # Combine past and future gas prices, ensuring no duplicates and sorting by date
    combined_gas_prices = pd.concat([past_gas_prices, future_gas_prices]).drop_duplicates(subset=DATE_FIELD).sort_values(by=DATE_FIELD).reset_index(drop=True)
    monthly_gas_prices_dataset.save_data(combined_gas_prices)

def fetch_gas_prices_and_forecast(process_only: bool) -> None:
    if not process_only:
        #fetch_gas_prices()
        fetch_gas_price_forecast()
    process_gas_prices()

def fetch_embedded_generation(process_only: bool) -> None:
    if process_only:
        return
    
    # fetch embedded generation data from Neso API and save to json file
    print('Fetching embedded generation data from Neso API...')

    embedded_generation = neso.fetch_neso_data(neso.EMBEDDED_FORECAST_ID)

    embedded_generation['EMBEDDED_FORECAST_TOTAL'] = embedded_generation['EMBEDDED_WIND_FORECAST'] + embedded_generation['EMBEDDED_SOLAR_FORECAST']
    embedded_generation.drop(columns=['DATE_GMT', 'TIME_GMT'], inplace=True)

    embedded_generation_source.save_data(embedded_generation)

def fetch_generation():
    if process_only:
        return
    
    def process_generation_data(additional: pd.DataFrame) -> pd.DataFrame:
        additional[DATETIME_FIELD] = pd.to_datetime(additional['DATETIME'])
        additional = (additional
            .drop(columns=['DATETIME'])
            .rename(columns={'WIND_EMB': 'Embedded Wind'})
            .rename(columns=dict(zip(additional.columns, [titlecase(col.replace('_', ' ').replace('perc', '(%)')) for col in additional.columns])))
        )
        return additional
    
    print('Fetching generation data from Neso API...')
    generation = generation_source.load_data() if generation_source.exists() else process_generation_data(generation_source.fetch_data())
    additional = neso.fetch_neso_data(neso.GENERATION_ID, offset=len(generation) if not generation.empty else 0, sort='DATETIME asc')

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
    bm_data = neso.fetch_all_records(neso.BALANCING_MECHANISM_ID)
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
    generation = lambda x: x.sum()/2  # Half the generation values to convert from MW to MWh for the half-hourly period
    aggregation_functions = [(col, 'sum') for col in list(NESO_GENERATION_TYPES.values()) + ['Total']]    
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
    
def fetch_cfd_data(process_only: bool):
    print('Fetching CFD data from Low Carbon Contracts Company...')
    cfd_locations_data = cfd_locations_source.fetch_data() if not process_only else cfd_locations_source.load_data() 
    cfd_contracts_data = cfd_contracts_source.fetch_data() if not process_only else cfd_contracts_source.load_data()
    cfd_settlements_data = cfd_settlements_source.fetch_data() if not process_only else cfd_settlements_source.load_data()

    # Merge the CFD locations and contracts data based on the 'CfD_Name' column
    cfd_locations_data = (cfd_locations_data
        .drop(columns=[
                'Constituency', 
                'Party',
                'MP_Name',
                'Country',
                'Technology_Type', 
                'Expected_Operational_Start_Date', 
                'Homes_Powered_Equivalent_Per_Annum',
                'Cars_Off_Road_Equivalent_Per_Annum'
            ])
    )

    def fix_cfd_columns(df: pd.DataFrame) -> pd.DataFrame:
        # Rename columns to match the expected format. 
        df = snake_case_to_capitalised(df)
        df = df.rename(columns={col: col.replace('CFD', 'CfD') for col in df.columns})
        df = df.rename(columns={'Name of CfD Unit': 'CfD Name'})
        df = fix_units(df)
        return df

    if not process_only:
        cfd_contracts_data = fix_cfd_columns(cfd_contracts_data)
        cfd_settlements_data = fix_cfd_columns(cfd_settlements_data)
        cfd_locations_data = fix_cfd_columns(cfd_locations_data)

    cfd_locations_data['Operational Start Date'] = pd.to_datetime(cfd_locations_data['Operational Start Date'], errors='coerce')

    cfd_settlements_data['Settlement Date'] = pd.to_datetime(cfd_settlements_data['Settlement Date'], errors='coerce')
    cfd_settlements_data['Year'] = cfd_settlements_data['Settlement Date'].dt.year
    cfd_settlements_data['CfD Payments (£/MWh)'] = cfd_settlements_data['CfD Payments (£)'] / cfd_settlements_data['CfD Generation (MWh)']

    cfd_contracts_data['Expected Start Date'] = pd.to_datetime(cfd_contracts_data['Expected Start Date'], errors='coerce')

    cfd_locations_source.save_data(cfd_locations_data)
    cfd_contracts_source.save_data(cfd_contracts_data)
    cfd_settlements_source.save_data(cfd_settlements_data)

    merged_cfd_data = pd.merge(cfd_locations_data, cfd_contracts_data, on='CfD Name', how='inner')
    cfd_dataset.save_data(merged_cfd_data)

monthly_weights = [
    1.2,
    1.05,
    1.09,
    0.93,
    0.88,
    0.86,
    0.9,
    0.88,
    0.9,
    1.04,
    1.12,
    1.15
]

forecasted_available_capacity = pd.Series({
    2027: 52.8,
    2028: 53.2,
    2029: 54.3,
    2030: 54.2,
    2031: 57.5,
    2032: 58.4,
    2033: 58.2,
    2034: 57.8,
    2035: 63.5,
    2036: 65.5,
    2037: 59.8,
    2038: 64.1,
    2039: 66.8,
    2040: 67.2
})

def fetch_cm_data(process_only):
    print("Fetching Capacity Market data from Low Carbon Contracts Company...")
    cm_payments = cm_payments_source.fetch_data() if not process_only else cm_payments_source.load_data()    
    cm_payments = snake_case_to_capitalised(fix_units(cm_payments))

    cm_awards = pd.DataFrame()
    capacity_auctions_dir = os.path.join(MANUAL_DATA_PATH, 'capacity-market')
    cm_auctions = cm_auctions_source.fetch_data() if not process_only else cm_auctions_source.load_data()

    # Merge the CM datasets in `data/manual/capacity-auctions`
    for filename in os.listdir(capacity_auctions_dir):
        print(f"Processing auction file: {filename}")
        if filename.endswith('.csv'):
            auction_data = ( 
                pd.read_csv(os.path.join(capacity_auctions_dir, filename))
                .drop(columns=['Parent Company', 'Bidding Company', 'CMU Name' ], errors='ignore')
            )
            #print(f"Processing auction file: {filename} with {len(auction_data)} records")
            auction_data["Duration (Years)"] = pd.to_numeric(auction_data["Duration (Years)"], errors='coerce').fillna(0) # Replace "N/A" with 0 in the "Duration" column
            auction_data['Capacity (MW)'] = pd.to_numeric(auction_data['Capacity (MW)'], errors='coerce').fillna(0)
            # if the auction_data does not have a Fuel Type column, add it with a default value of 'Unknown'
            if 'Fuel Type' not in auction_data.columns:
                auction_data['Fuel Type'] = 'Unknown'
            # append the delivery year and price columns from the cm_auctions dataframe to the auction_data dataframe based on the filename
            auction_name = os.path.splitext(filename)[0]
            auction_info = cm_auctions[cm_auctions['Auction Name'] == auction_name]
            if not auction_info.empty:
                auction_data['Delivery Year'] = auction_info['Delivery Year'].values[0]
                auction_data['Price'] = auction_info['Price'].values[0]
                auction_data['Price Year'] = auction_info['Price Year'].values[0]
                cm_awards = pd.concat([cm_awards, auction_data], ignore_index=True)
            else:
                print(f"Warning: No matching auction info found for {auction_name} in auctions.csv")

    cm_awards_source.save_data(cm_awards)
    cm_payments_source.save_data(cm_payments)
    cm_auctions_source.save_data(cm_auctions)
    
    # Append the auction data to estimate payments for future years by multiplying the price 
    # with the Quantity from the last known year and applying the inflator to adjust the price to the delivery year.
    # cm_forcast = pd.DataFrame()

    # for _, row in cm_awards.iterrows():
    #     if pd.isna(row['Delivery Year']):
    #         #print(f"Skipping row with Delivery Year for {row}")
    #         continue

    #     start_date = datetime(int(row['Delivery Year']), 11, 1)
    #     if start_date < datetime.now():
    #         start_date = datetime.now()
    #     next_date = datetime(int(row['Delivery Year']) + int(row['Duration']), 10, 1)
    #     if next_date > datetime.now() + timedelta(days=365*3):
    #         next_date = datetime(datetime.now().year + 3, datetime.now().month, 1)
    #     while next_date >= start_date:
    #         # Calculate the estimated payments for the month
    #         estimated_payments = row['Price'] * row['Quantity'] * monthly_weights[next_date.month - 1] * INFLATORS.get(next_date.year, 1.0)/INFLATORS.get(row['Price Year'], 1.0)
    #         # Append the estimated payments to the cm_forcast DataFrame if it does not already exist for that month overwise update the existing row with the new estimated payments
    #         forcast_row = pd.DataFrame({DATE_FIELD: [next_date], 'Capacity Payment': [estimated_payments], 'Quantity': [row['Quantity']]})
    #         cm_forcast = pd.concat([cm_forcast, forcast_row], ignore_index=True)
    #         next_date -= pd.DateOffset(months=1)

    # cm_forcast = cm_forcast.groupby(DATE_FIELD).agg({'Capacity Payment': 'sum', 'Quantity': 'sum'}).reset_index()

    cm_forecast = cm_forecast_source.fetch_data()
    cm_forecast = snake_case_to_capitalised(fix_units(cm_forecast))

    # Extend the cm_forecast DataFrame with remaining months of the last year given by taking the mean price and appliying the cm_weights to the remaining months of the last year in the cm_forecast DataFrame
    last_year = cm_forecast['Calendar Year'].max()
    last_year_data = cm_forecast[cm_forecast['Calendar Year'] == last_year]    
    print(last_year_data)

    for auction in last_year_data['Auction Identifier'].unique():
        base_cost = last_year_data[(last_year_data['Calendar Month'] == 1) & (last_year_data['Auction Identifier'] == auction)]['Monthly CM Forecast Cost (£)'].mean() / monthly_weights[0]
        print(f"Extending CM forecast for auction {auction} in year {last_year} with base cost {base_cost}")
        for month in range(last_year_data['Calendar Month'].max() + 1, 13):
            estimated_payments = base_cost * monthly_weights[month - 1] 
            forcast_row = pd.DataFrame({
                'Auction Identifier': [auction],
                'Calendar Year': [last_year], 
                'Calendar Month': [month], 
                'Monthly CM Forecast Cost (£)': [estimated_payments]})
            cm_forecast = pd.concat([cm_forecast, forcast_row], ignore_index=True)

    cm_forecast_source.save_data(cm_forecast)

    # Iterater over each month is the cm_forecast DataFrame if the quantity is less than forcasted_max_demand for that year
    # then estimate the additional payments needed to meet the forcasted_max_demand and add it to the cm_forecast DataFrame
    # for index, row in cm_forecast.iterrows():
    #     year = row[DATE_FIELD].year
    #     if year in forecasted_max_demand.index:
    #         if row['Quantity'] < forecasted_max_demand[year]:
    #             additional_quantity = forecasted_max_demand[year] - row['Quantity']
    #             additional_payments = additional_quantity * row['Capacity Payment'] / row['Quantity']
    #             cm_forcast.loc[index, 'Capacity Payment'] += additional_payments
    #             cm_forcast.loc[index, 'Quantity'] += additional_quantity
    # cm_forcast.to_csv(os.path.join(TRANSFORMED_DATA_PATH, 'capacity_market_forecast.csv'), index=False)

def local_data_sources(process_only: bool) -> None:
    data = capacity_factors_source.fetch_data()
    data[DATE_FIELD] = pd.to_datetime(data[DATE_FIELD], format='%d/%m/%y', errors='coerce')
    
    capacity_factor_constant = 100000/(91.5*24)
    for fuel_type in ['Onshore Wind', 'Offshore Wind', 'Solar']:
        data[f'{fuel_type} Capacity Factor (%)'] = capacity_factor_constant * data[f'{fuel_type} Generation (GWh)'] / data[f'{fuel_type} Capacity (MW)'] 
    capacity_factors_source.save_data(data)

def create_metric(metric: Metric, values: list[float]) -> None:
    latest_value, previous_value, five_years_ago_value = values
    calc_change = lambda current, previous: ((current - previous) / previous) * 100 if previous != 0 else np.nan
    metric.current = latest_value
    metric.annual_change = calc_change(latest_value, previous_value)
    metric.change_from_5_years_ago = calc_change(latest_value, five_years_ago_value)
    metric.save()

def create_aggregate_metric(time_frames: list[tuple[int, int]], metric: Metric, df: pd.DataFrame, metric_column: str, agg_type="sum") -> None:
    '''
    Input: A dataframe with a 'Metric' column and a 'Date' column
    '''
    print(f"Creating metric {metric.name} with aggregation type {agg_type}...")
    get_offset = lambda months: pd.Timestamp.now() - pd.DateOffset(months=months)
    values = []
    for lower_bound, upper_bound in time_frames:
        filtered_df = df[(df[DATE_FIELD] >= get_offset(lower_bound)) & (df[DATE_FIELD] <= get_offset(upper_bound))]
        if filtered_df.empty:
            print(f"Warning: No data found for {metric.name} in the range of {lower_bound} to {upper_bound} months ago.")

        if agg_type == "sum":
            values.append(filtered_df[metric_column].sum())
        elif agg_type == "mean":
            values.append(filtered_df[metric_column].mean())
        else:
            raise ValueError(f"Unsupported aggregation type: {agg_type}")
    
    create_metric(metric, values)

create_monthly_metric = partial(create_aggregate_metric, [(1, 0), (13, 12), (61, 60)])
create_annual_metric = partial(create_aggregate_metric, [(13, 1), (25, 13), (73, 61)])
create_total_metric = partial(create_aggregate_metric, [(1000, 0), (1000, 12), (1000, 60)])

def create_metrics(process_only: bool):
    '''
    Create metrics for the electricity market including 
        - total gas cost
        - total wholesale cost
        - total CFD payments
        - total capacity market payments
        The metrics are created by creating a dataframe with the with date and metric columns and passing it to `Metric.create_metric`
    '''
    print("Creating metrics...")
    gasvselec = gasvselec_dataset.load_data()
    cfd_settlements = cfd_settlements_source.load_data()
    cm_payments = cm_payments_source.load_data()
    cfd_locations = cfd_locations_source.load_data()
    bm_payments = bm_payments_source.load_data()
    wholesale_cost = wholesale_price_source.load_data()

    gasvselec['Gas Cost'] = gasvselec['Gas Price'] * gasvselec['Gas'] * 2.5
    gasvselec['Wholesale Cost'] = gasvselec['Electricity Price'] * gasvselec['Total']

    cfd_settlements[DATE_FIELD] = pd.to_datetime(cfd_settlements['Settlement Date'], errors='coerce')
    cfd_settlements = cfd_settlements.groupby(DATE_FIELD).agg({'CfD Payments (£)': 'sum'}).reset_index()

    cfd_locations[DATE_FIELD] = pd.to_datetime(cfd_locations['Operational Start Date'], errors='coerce')

    cm_payments[DATE_FIELD] = pd.to_datetime(cm_payments['Calendar Year'].astype(str) + '-' + cm_payments['Calendar Month'].astype(str) + f"-{datetime.today().day}", errors='coerce')
    cm_payments = cm_payments.groupby(DATE_FIELD).agg({'Capacity Payment (£)': 'sum', "Auction Acquired Capacity Obligation (MW)": 'sum'}).reset_index()
    
    bm_payments["Total"] = bm_payments[['Energy Imbalance', 'Frequency Control', 'Positive Reserve', 'Constraints', 'Negative Reserve', 'Other']].sum(axis=1)

    create_monthly_metric(current_gas_price_metric, gasvselec, "Gas Price", "mean")
    create_annual_metric(total_gas_cost_metric, gasvselec, "Gas Cost")
    create_monthly_metric(sparkgap_metric, gasvselec, "Ratio", "mean")
    create_monthly_metric(current_wholesale_price_metric, gasvselec, "Electricity Price", "mean")
    create_annual_metric(total_wholesale_cost_metric, gasvselec, "Wholesale Cost")
    create_annual_metric(total_generation_metric, gasvselec, "Total")
    create_annual_metric(total_cfd_payments_metric, cfd_settlements, "CfD Payments (£)")
    create_total_metric(total_cfd_capacity_metric, cfd_locations, "Maximum Contract Capacity (MW)")
    create_annual_metric(total_cm_payments_metric, cm_payments, "Capacity Payment (£)")
    create_annual_metric(total_cm_capacity_metric, cm_payments, "Auction Acquired Capacity Obligation (MW)")
    create_annual_metric(annual_bm_payments_metric, bm_payments, "Total")
    
fetch_functions_list: list[tuple[Callable[[bool], None], str]] = [
    (fetch_generation_and_prices, "Generation and Prices Data"),
    (fetch_demand, "Demand Data"),
    (fetch_embedded_generation, "Embedded Generation Data"),
    (merge_generators, "Update List of Generators"),
    (fetch_balancing_mechanism_data, "Balancing Mechanism Data"),
    (fetch_gas_prices_and_forecast, "Gas Prices Data"),
    (fetch_cfd_data, "CFD Data"),
    (fetch_cm_data, "Capacity Market Data"),
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
            fetch_functions[opt][0](process_only)
        else:
            print(f"Invalid option: {opt}. Skipping.")