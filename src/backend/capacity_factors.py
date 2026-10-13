from datetime import date
from io import BytesIO
import pandas as pd
from titlecase import titlecase

from . import fetch_from_url
from constants import CAPACITY_FACTORS, DATE_FIELD
from datasources.supply import *


def fetch_and_process_capacity_data():
    """
    Calculates the capacity factors generation and capacity data.
    For each quarter it calculates the average, minimum, and maximum capacity factors for daily, weekly, and monthly periods.
    """
    biomass_columns = [
        'Landfill Gas',
        'Sewage Sludge Digestion',
        'Energy From Waste',
        'Animal Biomass (Non-Ad)',
        'Anaerobic Digestion',
        #'Plant Biomass',
        'Liquid Biofuels'
    ]
    def process_table(df: pd.DataFrame) -> pd.DataFrame:
        df = df.transpose().reset_index()
        df.columns = df.iloc[0]
        df = df.drop(0).reset_index(drop=True)
        # Remove "[Note 1]" from the column names
        df.columns = [titlecase(col.split("[")[0].strip()) for col in df.columns]
        df.rename(columns={'Shoreline Wave / Tidal': 'Tidal', 'Solar Photovoltaics': 'Solar', 'Solar PV': 'Solar', 'Plant Biomass': 'Biomass'}, inplace=True)
        df.columns = [DATE_FIELD] + list(df.columns[1:])

        # Replace "[x]" with 0
        df = df.replace("[x]", 0)

        # First column is the in the format "2026\n 1st quater", we want to convert it to a date in the format "YYYY-MM-DD" representing the first day of the quarter
        def convert_quarter_to_date(quarter_str):
            year, quarter = quarter_str.split("\n")
            month = int(quarter[0]) * 3
            return date(year=int(year), month=month, day=31 if month == 12 else 30)
        df[DATE_FIELD] = df[DATE_FIELD].apply(convert_quarter_to_date)

        return df
    
    spreadsheet = BytesIO(fetch_from_url("https://assets.publishing.service.gov.uk/media/6aba724dfceb6fb3a65012d2/ET_6.1_SEP_26.xlsx"))
    uk_capacity = process_table(pd.read_excel(spreadsheet, sheet_name="Quarter", skiprows=6, nrows=14))
    ni_capacity = process_table(pd.read_excel(spreadsheet, sheet_name="Northern Ireland - Qtr", skiprows=6, nrows=14))
    uk_generation = process_table(pd.read_excel(spreadsheet, sheet_name="Quarter", skiprows=24, nrows=13))
    ni_generation = process_table(pd.read_excel(spreadsheet, sheet_name="Northern Ireland - Qtr", skiprows=23, nrows=8))

    # For capacity dataframes collapse "Large Hydro" and "Small Hydro" into a single "Hydro" column, and collapse "Onshore Wind" and "Offshore Wind" into a single "Wind" column
    for df in [uk_capacity, ni_capacity]:
        df['Hydro'] = df['Large Scale Hydro'] + df['Small Scale Hydro']
        df['Offshore Wind'] = df['Offshore Wind - Seabed'] + df['Offshore Wind - Floating']
        df.drop(columns=['Large Scale Hydro', 'Small Scale Hydro', 'Offshore Wind - Seabed', 'Offshore Wind - Floating'] + biomass_columns, inplace=True)

    uk_generation = uk_generation.drop(columns=biomass_columns + ['Co-Firing With Fossil Fuels'])

    ni_biomass_columns = [
        'Landfill Gas',
        'Sewage Sludge Digestion',
        'Other Biomass (Inc. Co-Firing)'
    ]
    ni_generation['Biomass'] = ni_generation['Other Biomass (Inc. Co-Firing)']
    ni_generation.drop(columns=ni_biomass_columns, inplace=True)

    # Create capacity dataset by subtracting ni_capacity from uk_capacity
    gb_capacity = pd.merge(uk_capacity, ni_capacity, on=DATE_FIELD, suffixes=('', '_ni'))
    gb_generation = pd.merge(uk_generation, ni_generation, on=DATE_FIELD, suffixes=('', '_ni'))

    for df in [gb_capacity, gb_generation]:
        for col in CAPACITY_FACTORS:
            df[col] = df[col] - df[col + '_ni']
            df.drop(columns=[col + '_ni'], inplace=True)

    gb_capacity_factors = pd.merge(gb_capacity, gb_generation, on=DATE_FIELD, suffixes=('', '_gen'))
    gb_capacity_factors['Days'] = gb_capacity_factors[DATE_FIELD].apply(lambda x: [90, 91, 92, 92][(x.month//3)-1])
    for col in CAPACITY_FACTORS:
        gb_capacity_factors[col] = (100000 * gb_capacity_factors[col + '_gen']) / (gb_capacity_factors[col] * 24 * gb_capacity_factors['Days'])
        gb_capacity_factors.drop(columns=[col + '_gen'], inplace=True)
    gb_capacity_factors.drop(columns=['Days'], inplace=True)

    for df in [gb_capacity, gb_capacity_factors]:
        for col in CAPACITY_FACTORS:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    capacity_source.save_data(gb_capacity)
    capacity_factors_source.save_data(gb_capacity_factors)

def create_capacity_factor_dataset():
    print("Calculating capacity factors...")
    capacity, generation = capacity_factors_dataset.base_data()
    capacity['Wind'] = capacity['Onshore Wind'] + capacity['Offshore Wind']
    generation['Wind'] = generation['Wind'] + generation['Embedded Wind']
    
    # Interpolate capacity factors for missing dates
    print(capacity.tail())
    capacity = (
        capacity
        .set_index(DATE_FIELD).reindex(pd.date_range(start=capacity[DATE_FIELD].min(), end=capacity[DATE_FIELD].max(), freq='D'))
        .interpolate(method='time').reset_index().rename(columns={'index': DATE_FIELD})
    )

    merged = pd.merge(generation, capacity, on=DATE_FIELD, suffixes=(' Generation', ' Capacity'))
    keep_columns = [DATE_FIELD]
    
    for window in [('Daily', 1), ('Weekly', 7), ('Monthly', 30), ('Quarterly', 90)]:
        for gen_type in [cf for cf in CAPACITY_FACTORS if cf + ' Generation' in merged.columns] + ['Wind']:
            name = f'{gen_type} Capacity Factor ({window[0]})'

            #merged[f'{gen_type} Generation ({window[0]})'] = merged[f'{gen_type} Generation'].rolling(window=window[1]).mean()
            #merged[f'{gen_type} Capacity ({window[0]})'] = merged[f'{gen_type} Capacity'].rolling(window=window[1]).mean()
            merged[name] = (merged[f'{gen_type} Generation'].rolling(window=window[1]).mean() * 100) / (merged[f'{gen_type} Capacity'].rolling(window=window[1]).mean() * 24)
            keep_columns += [name]

    merged = merged.drop(columns=[col for col in merged.columns if col not in keep_columns])
    print(merged.tail())
    capacity_factors_dataset.save_data(merged)

def create_capacity_factor_data(process_only: bool) -> None:
    print("Creating capacity factor data...")
    if not process_only:
        fetch_and_process_capacity_data()
    create_capacity_factor_dataset()
