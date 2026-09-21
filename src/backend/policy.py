import os
import pandas as pd
from  datasources.policy import *
from backend.helpers import snake_case_to_capitalised
from .ckan import CKANClient, Endpoint

lccc_client = CKANClient(base_url="https://dp.lowcarboncontracts.uk")
CFD_LOCATIONS = Endpoint("3f31f008-0b51-4b5b-9679-4be416509a75", lccc_client)
CM_FORECAST = Endpoint("a3b6a6bf-6b18-412b-9433-e1fe4a3d1ca1", lccc_client)
CM_PAYMENTS = Endpoint("2ed26d4f-ceb0-4a96-895e-4a3cc38c788c", lccc_client)
CFD_FORECAST = Endpoint("b8820220-ee2e-451d-acf9-deafc374c989", lccc_client)
CFD_CONTRACTS = Endpoint("fdaf09d2-8cff-4799-a5b0-1c59444e492b", lccc_client)

cm_monthly_weights = [
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

def fix_lccc_units(df: pd.DataFrame) -> pd.DataFrame:
    def do_fix(col: str) -> str:
        for match in [('GBP Per MWh', '£/MWh'), ('MWh', 'MWh'), ('MW', 'MW'), ('GBP', '£'), ('CO2e', 'CO2e')]:
            if match[0] in col:
                return col.replace(match[0], f'({match[1]})')
        return col

    df = df.rename(columns={col: do_fix(col) for col in df.columns})

    # Coerce numeric columns to numeric types
    for col in df.columns:
        if df[col].dtype == 'str':
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass  # If conversion fails, keep the original data
    return df

lccc_items = [
    (
        'cfd_locations', 
        CFD_LOCATIONS, 
        cfd_locations_source, 
        lambda df: df.assign(**{
            'Operational Start Date': pd.to_datetime(df['Operational Start Date'], errors='coerce'),
            'Expected Operational Start Date': pd.to_datetime(df['Expected Operational Start Date'], errors='coerce'),
        }).drop(columns=[
            'Constituency', 
            'Party', 
            'MP Name', 
            'Country', 
            'Technology Type', 
            'Homes Powered Equivalent Per Annum', 
            'Cars Off Road Equivalent Per Annum'
        ])
    ),
    (
        'cfd_contracts', 
        CFD_CONTRACTS, 
        cfd_contracts_source,
        lambda df: df.assign(**{
            'Expected Start Date': pd.to_datetime(df['Expected Start Date'], errors='coerce'),
            'Maximum Contract Capacity (MW)': pd.to_numeric(df['Maximum Contract Capacity (MW)'], errors='coerce').fillna(0)
        })
    ),
    (
        'cfd_settlements', 
        CFD_FORECAST, 
        cfd_settlements_source,
        lambda df: df.assign(**{
            'Date': pd.to_datetime(df['Settlement Date'], errors='coerce'),
            'Year': pd.to_datetime(df['Settlement Date'], errors='coerce').dt.year,
            'CfD Payments (£/MWh)': df['CfD Payments (£)'] / df['CfD Generation (MWh)']
        })
    ),
    (
        'cm_payments', 
        CM_PAYMENTS,
        cm_payments_source,
        lambda df: df.assign(**{
            'Date': pd.to_datetime(df['Calendar Year'].astype(str) + '-' + df['Calendar Month'].astype(str) + "-01", errors='coerce')
        })
    ),
    (
        'cm_forecast', 
        CM_FORECAST,
        cm_forecast_source,
        lambda df: df,
    )
]

def fetch_lccc_data(process_only: bool):
    print('Fetching CFD data from Low Carbon Contracts Company...')

    def fix_lccc_columns(df: pd.DataFrame) -> pd.DataFrame:
        # Rename columns to match the expected format. 
        df = snake_case_to_capitalised(df)
        df = df.rename(columns={col: col.replace('CFD', 'CfD') for col in df.columns})
        df = df.rename(columns={'Name of CfD Unit': 'CfD Name'})
        df = fix_lccc_units(df)
        return df

    for item_name, endpoint, source, transform_func in lccc_items:
        if not process_only:
            print(f"Fetching {item_name} data from CKAN...")
            old_data = source.load_data() if source.exists() else pd.DataFrame()
            new_data = endpoint(len(old_data))
            if not new_data.empty:
                new_data = transform_func(fix_lccc_columns(new_data))
                source.save_data(pd.concat([old_data, new_data], ignore_index=True))

    cfd_locations_data, cfd_contracts_data = cfd_dataset.base_data()
    merged_cfd_data = pd.merge(cfd_locations_data, cfd_contracts_data, on='CfD Name', how='inner')
    cfd_dataset.save_data(merged_cfd_data)
   
    cm_auctions = cm_auctions_source.load_data() if cm_auctions_source.exists() else pd.read_csv(os.path.join(MANUAL_DATA_PATH, 'cm-auctions.csv'))
    cm_awards = pd.DataFrame()
    capacity_auctions_dir = os.path.join(MANUAL_DATA_PATH, 'capacity-market')

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
    cm_forecast, = cm_extended_forecast_dataset.base_data()
    
    # Extend the cm_forecast DataFrame with remaining months of the last year given by taking the mean price and appliying the cm_weights to the remaining months of the last year in the cm_forecast DataFrame
    last_year = cm_forecast['Calendar Year'].max()
    last_year_data = cm_forecast[cm_forecast['Calendar Year'] == last_year]    

    for auction in last_year_data['Auction Identifier'].unique():
        base_cost = last_year_data[(last_year_data['Calendar Month'] == 1) & (last_year_data['Auction Identifier'] == auction)]['Monthly CM Forecast Cost (£)'].mean() / cm_monthly_weights[0]
        print(f"Extending CM forecast for auction {auction} in year {last_year} with base cost {base_cost}")
        for month in range(last_year_data['Calendar Month'].max() + 1, 13):
            estimated_payments = base_cost * cm_monthly_weights[month - 1] 
            forcast_row = pd.DataFrame({
                'Auction Identifier': [auction],
                'Calendar Year': [last_year], 
                'Calendar Month': [month], 
                'Monthly CM Forecast Cost (£)': [estimated_payments]})
            cm_forecast = pd.concat([cm_forecast, forcast_row], ignore_index=True)

    cm_extended_forecast_dataset.save_data(cm_forecast)

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
    
    