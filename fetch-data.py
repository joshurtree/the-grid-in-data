#Fetches and cleans the data from the GB electricity market, returning a DataFrame with the relevant columns.
from bs4 import BeautifulSoup
from datetime import date, datetime, timezone, timedelta
from io import StringIO,BytesIO
import numpy as np
import os
from OSGridConverter import grid2latlong, OSGridReference
import pandas as pd
import random
import requests
import sys
from tqdm import tqdm

from backend.bmrs import fetch_FPN, fetch_extended_bmrs_data, fetch_bmrs_data
from backend.neso import fetch_embedded_generation
from backend.constants import INFLATORS, MANUAL_DATA_DIR, NESO_GENERATION_TYPES, RAW_DATA_DIR, TRANSFORMED_DATA_DIR


def fetch_monthly_gas_prices():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get("https://poundf.co.uk/uk-natural-gas", headers=headers)
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
            cols[0] = f"{year}-{cols[0]}"
            rows.append(cols[:2])

    if not rows:
        raise RuntimeError("No data rows found in the table")

    future_gas_prices = pd.DataFrame(rows, columns=["Date", "Price"])
    future_gas_prices['Date'] = pd.to_datetime(future_gas_prices['Date'], format='%Y-%b')
    future_gas_prices['Price'] = pd.to_numeric(future_gas_prices['Price'], errors='coerce')
    # Convert from p/therm to p/kWh and round to 4 decimal places
    future_gas_prices['Price'] = round(future_gas_prices['Price']/29.3071, 4)
    
    gas_prices = pd.read_csv(os.path.join(RAW_DATA_DIR, 'system_gas_prices.csv'))
    gas_prices['Date'] = pd.to_datetime(gas_prices['Date'])
    gas_prices.drop(columns=['SAP seven-day rolling average'], inplace=True)

    past_gas_prices = gas_prices.resample('MS', on='Date').first().reset_index()
    # Combine past and future gas prices, ensuring no duplicates and sorting by date
    combined_gas_prices = pd.concat([past_gas_prices, future_gas_prices]).drop_duplicates(subset='Date').sort_values(by='Date').reset_index(drop=True)
    combined_gas_prices.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'monthly_gas_prices.csv'), index=False)

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

def fetch_generation_and_prices():
    # Load data from CSV files
    generation = fetch_generation() if '1' in option else pd.read_csv(os.path.join(RAW_DATA_DIR, 'generation.csv'), index_col='DATETIME', parse_dates=True)
    prices = fetch_prices() if '2' in option else pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'market-prices.csv'), index_col='DATETIME', parse_dates=True)

    print(f'[DEBUG] Loaded {len(generation)} generation records and {len(prices)} price records')
    
    merged = pd.merge(prices, generation, on='DATETIME', how='inner')
    # Rename columns to match expected format
    merged = merged.rename(columns={'GENERATION': 'Total'})
    merged['SettlementDate'] = pd.to_datetime(merged['SettlementDate'])    

    # Drop rows where there is not 48 settlement periods in a day (i.e. incomplete days)
    merged = merged.groupby('SettlementDate').filter(lambda x: len(x) == 48)

    # Define aggregation functions for each column: sum for generation columns and total
    aggregation_functions = {col: 'sum' for col in list(NESO_GENERATION_TYPES.keys()) + ['Total']}

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

    # Combine the aggregation mapping
    agg_map = dict(aggregation_functions)
    agg_map['Price'] = weighted_price

    # Group by date and calculate aggregated sums + weighted price
    daily_data = merged.groupby('SettlementDate').agg(agg_map).reset_index()
    for gen_type in NESO_GENERATION_TYPES.keys():
        daily_data[gen_type + '_perc'] = (daily_data[gen_type] / daily_data['Total']) * 100
    daily_data = daily_data.sort_values(by='SettlementDate').reset_index(drop=True)

    # save the cleaned data to a new CSV file
    daily_data.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'daily_data.csv'), index=False)
    merged.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'half_hourly_data.csv'), index=False)

def fetch_cfd_data():
    print('Fetching CFD data from Low Carbon Contracts Company...')
    # Download the CSV file from the provided URL and save it to the RAW_DATA_DIR
    cfd_url = "https://dp.lowcarboncontracts.uk/dataset/8e8ca0d5-c774-4dc8-a079-347f1c180c0f/resource/5279a55d-4996-4b1e-ba07-f411d8fd31f0/download/actual_cfd_generation_and_avoided_ghg_emissions.csv"
    cfd_data = pd.read_csv(cfd_url)
    cfd_data.to_csv(os.path.join(RAW_DATA_DIR, 'cfd_settlements.csv'), index=False)

    cfd_locations_url = "https://dp.lowcarboncontracts.uk/dataset/423d3c6b-d1ea-466d-a0f2-5d169003fe56/resource/f1416517-a6ff-4cd1-a364-22015a942a3f/download/cfd_locations_by_parliamentary_constituency.csv"
    cfd_locations_data = pd.read_csv(cfd_locations_url)
    cfd_locations_data.to_csv(os.path.join(RAW_DATA_DIR, 'cfd_locations.csv'), index=False)

    cfd_contracts_url = "https://dp.lowcarboncontracts.uk/dataset/754ae1ec-3539-4bdf-86f5-ba204a56be76/resource/7bdfb0cb-fe99-44eb-b07b-2047e82f5601/download/cfd_contract_portfolio_status.csv"
    cfd_contracts_data = pd.read_csv(cfd_contracts_url)
    cfd_contracts_data.to_csv(os.path.join(RAW_DATA_DIR, 'cfd_contracts.csv'), index=False)

    # Merge the CFD locations and contracts data based on the 'CfD_Name' column
    cfd_locations_data = (cfd_locations_data
        .drop(columns=[
                'Constituency', 
                'Party',
                'MP_Name',
                'Country',
                'Technology_Type', 
                'Operational_Start_Date', 
                'Expected_Operational_Start_Date', 
                'Maximum_Contract_Capacity_MW',
                'Homes_Powered_Equivalent_Per_Annum',
                'Cars_Off_Road_Equivalent_Per_Annum'
            ])
    )
    cfd_contracts_data = cfd_contracts_data.rename(columns={'Name_of_CFD_Unit': 'CfD_Name'})
    merged_cfd_data = pd.merge(cfd_locations_data, cfd_contracts_data, on='CfD_Name', how='inner')
    merged_cfd_data.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'cfd_data.csv'), index=False)

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

def fetch_cm_data():
    print("Fetching Capacity Market data from Low Carbon Contracts Company...")
    cm_payments = pd.read_csv("https://dp.lowcarboncontracts.uk/dataset/ea55663a-30b2-4b74-b72c-946de1622167/resource/1c4daa32-2358-43d4-b2d1-29e948c159cd/download/capacity_obligation_by_auction.csv")
    cm_payments.to_csv(os.path.join(RAW_DATA_DIR, 'capacity_obligation_by_auction.csv'), index=False)

    cm_awards = pd.DataFrame()
    capacity_auctions_dir = os.path.join(RAW_DATA_DIR, 'capacity-market')
    cm_auctions = pd.read_csv(os.path.join(RAW_DATA_DIR, 'auctions.csv'))

    # Merge the CM datasets in `data/raw/capacity-auctions`
    for filename in os.listdir(capacity_auctions_dir):
        if filename.endswith('.csv'):
            auction_data = ( 
                pd.read_csv(os.path.join(capacity_auctions_dir, filename))
                .rename(columns={
                    'Capacity (MW)': 'Quantity',
                    'Duration (Years)': 'Duration',
                })
                .drop(columns=['Parent Company', 'Bidding Company', 'CMU Name' ], errors='ignore')
            )
            #print(f"Processing auction file: {filename} with {len(auction_data)} records")
            auction_data["Duration"] = pd.to_numeric(auction_data["Duration"], errors='coerce').fillna(0) # Replace "N/A" with 0 in the "Duration" column
            auction_data['Quantity'] = pd.to_numeric(auction_data['Quantity'], errors='coerce').fillna(0)
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

    cm_awards.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'capacity_auction_awards.csv'), index=False)
    
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
    #         forcast_row = pd.DataFrame({'Date': [next_date], 'Capacity Payment': [estimated_payments], 'Quantity': [row['Quantity']]})
    #         cm_forcast = pd.concat([cm_forcast, forcast_row], ignore_index=True)
    #         next_date -= pd.DateOffset(months=1)

    # cm_forcast = cm_forcast.groupby('Date').agg({'Capacity Payment': 'sum', 'Quantity': 'sum'}).reset_index()

    cm_forcast = pd.read_csv("https://dp.lowcarboncontracts.uk/dataset/a90f0e9b-d894-4d80-bedd-608a837d5e5d/resource/011a729d-5e58-4247-838e-601fd9bcf8d1/download/cm_forecast_cost.csv")
    cm_forcast.to_csv(os.path.join(RAW_DATA_DIR, 'neso_capacity_market_forecast.csv'), index=False)
    
    # Iterater over each month is the cm_forcast DataFrame if the quantity is less than forcasted_max_demand for that year
    # then estimate the additional payments needed to meet the forcasted_max_demand and add it to the cm_forcast DataFrame
    # for index, row in cm_forcast.iterrows():
    #     year = row['Date'].year
    #     if year in forecasted_max_demand.index:
    #         if row['Quantity'] < forecasted_max_demand[year]:
    #             additional_quantity = forecasted_max_demand[year] - row['Quantity']
    #             additional_payments = additional_quantity * row['Capacity Payment'] / row['Quantity']
    #             cm_forcast.loc[index, 'Capacity Payment'] += additional_payments
    #             cm_forcast.loc[index, 'Quantity'] += additional_quantity
    cm_forcast.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'capacity_market_forecast.csv'), index=False)

fetch_functions = {
    'A': fetch_generation_and_prices,
    'B': fetch_generation_and_prices,
    'C': fetch_demand,
    'D': fetch_embedded_generation,
    'E': fetch_system_prices,
    'F': merge_generators,
    'G': fetch_monthly_gas_prices,
    'H': fetch_cfd_data,
    'I': fetch_cm_data
}

def show_menu():
    print("Select the data to fetch and process. Available options:")
    print("A. Generation Data")
    print("B. Price Data")
    print("C. Demand Data")
    print("D. Embedded Generation Data")
    print("E. System Prices Data")
    print("F. Update List of Generators")
    print("G. Monthly Gas Prices Data")
    print("H. CFD Data")
    print("I. Capacity Market Data")
    print("#. All Data (default)")
    option = input("Enter the option letter (A-I, #): ").strip().upper()
    if option == '#' or option == '':
        option = 'ABCDEFGHI'

    return option

if __name__ == "__main__":
    # If --fetch-all is passed as an argument, fetch all data
    
    if '--fetch-all' in sys.argv:
        option = 'ABCDEFGHI'
    else:
        option = show_menu()

    for opt in option:
        if opt in fetch_functions:
            fetch_functions[opt]()
        else:
            print(f"Invalid option: {opt}. Skipping.")