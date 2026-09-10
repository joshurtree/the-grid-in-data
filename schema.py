from datasources import *

# Display the schema of the dataframes on the console for debugging purposes
def display_schema(df, name):
    print(f"Schema for {name}:")
    print(df.dtypes)
    print(df.head())

# select the dataframe to display schema for
if __name__ == "__main__":
    dataframes = [
        ("Daily Dataset", daily_dataset.load_data()),
        ("Gas vs Elec Dataset", gasvselec_dataset.load_data()),
        ("CFD Settlements", cfd_settlements_source.load_data()),
        ("Capacity Market Payments", cm_payments_source.load_data()),
        ("Wholesale Price", wholesale_price_source.load_data()),
        ("Gas Price", daily_gas_prices_dataset.load_data()),
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
