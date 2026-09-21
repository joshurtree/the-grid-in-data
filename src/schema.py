from datasources import *

# Display the schema of the dataframes on the console for debugging purposes
def display_schema(df, name):
    print(f"Schema for {name}:")
    print(df.dtypes)
    print(df.head())
    print("...")
    print(df.tail())

# select the dataframe to display schema for
if __name__ == "__main__":
    dataframes = [
        ("BM Payments", bm_payments_source.load_data()),
        ("Daily Dataset", daily_dataset.load_data()),
        ("Gas vs Elec Dataset", gasvselec_dataset.load_data()),
        ("CFD Settlements", cfd_settlements_source.load_data()),
        ("CFD Contracts", cfd_contracts_source.load_data()),
        ("CFD Locations", cfd_locations_source.load_data()),
        ("Capacity Market Payments", cm_payments_source.load_data()),
        ("Capacity Market Forecast", cm_forecast_source.load_data()),
        ("Wholesale Price", wholesale_price_source.load_data()),
        ("Gas Price", daily_gas_prices_dataset.load_data()),
        ("Monthly Gas Price", monthly_gas_prices_dataset.load_data()),
        #("Renewables Obligation", ro_source.load_data()),
        ("CM Auctions", cm_auctions_source.load_data()),
        ("CM Awards", cm_awards_source.load_data()),
        #("Generators", generators_dataset.load_data()),
        ("Capacity Factors", capacity_factors_source.load_data()),
        ("Gas Storage", gas_storage_dataset.load_data()),
        ("Gas Demand", gas_demand_source.load_data()),
        ("Gas Price Forecast", gas_price_forecast_source.load_data()),
    ]

    for (i, (name, df)) in enumerate(dataframes):
        print(f"{i+1}: {name}")

    print("Select a number to display the schema for that dataframe, or 'q' to quit.")
    user_input = input("Enter your choice: ")
    if user_input.lower() == 'q':
        exit()
    try:
        choice = int(user_input)
        if 1 <= choice <= len(dataframes):
            name, df = dataframes[choice - 1]
            display_schema(df, name)
        else:
            print("Invalid choice. Please select a valid number.")
    except ValueError:
        print("Invalid input. Please enter a number or 'q' to quit.")
