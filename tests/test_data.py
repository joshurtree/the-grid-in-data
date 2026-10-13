from datetime import datetime, timezone, tzinfo
import pandas as pd
import numpy as np
import pytz

import pytest
from backend import metrics
from constants import DATE_FIELD, DATETIME_FIELD
from datasources import *
from functools import partial

test_demand= demand_source.load_data()
actual_demand = pd.read_csv('data/manual/annual-demand.csv')

def calc_demand(start_date: datetime, end_date: datetime) -> float:
    '''
    Calculate the annual demand for a given year from the provided DataFrame.
    '''
    filtered_demand = test_demand[(test_demand[DATETIME_FIELD] >= start_date) & (test_demand[DATETIME_FIELD] <= end_date)]
    print(filtered_demand['National Demand'].mean())
    # Calculate the total demand for the year
    total_demand = filtered_demand['National Demand'].sum() / 2000
    expected_demand = pd.to_numeric(actual_demand[actual_demand['Components of supply and demand'] == 'Final consumption'][str(start_date.year)].values[0])
    print(f"Year: {start_date.year}, Total Demand: {total_demand}, Expected Demand: {expected_demand}")
    return abs(total_demand - expected_demand) / expected_demand

# # Use pytest's parametrize to run the test for each year
# @pytest.mark.parametrize("year", range(2009, 2026))
# def test_annual_demand(year: int) -> None:
#     '''
#     Test annual demand data vs DUKES data for each year from 2009 to 2025.
#     '''
#     rel_difference = calc_demand(datetime(year, 1, 1, tzinfo=pytz.UTC), datetime(year, 12, 31, 23, 59, 59, tzinfo=pytz.UTC))
#     assert rel_difference < 0.01, f"Mismatch in demand for year {year}:  relative difference {rel_difference:.2f}"

def test_gasvselec_dataset() -> None:
    '''
    Test the gasvselec dataset for expected columns and non-empty data.
    '''
    df = gasvselec_dataset.load_data()
    assert not df.empty, "Gas vs Electricity dataset is empty."
    # Check number of records for 2025
    records_2025 = df[df['Date'].dt.year == 2025]
    assert not records_2025.empty, "No records found for 2025."
    assert len(records_2025) == 365, "Expected 365 records for 2025, but found a different number."