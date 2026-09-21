from functools import partial
import numpy as np
import pandas as pd

from constants import DATE_FIELD
from datasources import (
    gasvselec_dataset,
    cfd_settlements_source,
    cm_payments_source,
    cfd_locations_source,
    bm_payments_source,
    wholesale_price_source,
    gas_storage_dataset,
    current_gas_price_metric,
    total_gas_cost_metric,
    sparkgap_metric,
    current_wholesale_price_metric,
    total_wholesale_cost_metric,
    total_generation_metric,
    total_cfd_payments_metric,
    total_cfd_capacity_metric,
    total_cm_payments_metric,
    total_cm_capacity_metric,
    annual_bm_payments_metric,
    gas_storage_metric
)

from figures.metric import Metric

def create_metric(metric: Metric, values: list[float]) -> None:
    print(f"Creating metric {metric.name} with values: {values}")
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
    gas_storage = gas_storage_dataset.load_data()
    
    gasvselec['Gas Cost'] = gasvselec['Gas Price'] * gasvselec['Gas'] * 2.5
    gasvselec['Wholesale Cost'] = gasvselec['Electricity Price'] * gasvselec['Total']

    cfd_settlements[DATE_FIELD] = pd.to_datetime(cfd_settlements['Settlement Date'], errors='coerce')
    cfd_settlements = cfd_settlements.groupby(DATE_FIELD).agg({'CfD Payments (£)': 'sum'}).reset_index()

    cfd_locations[DATE_FIELD] = pd.to_datetime(cfd_locations['Operational Start Date'], errors='coerce')

    #cm_payments[DATE_FIELD] = pd.to_datetime(cm_payments['Calendar Year'].astype(str) + '-' + cm_payments['Calendar Month'].astype(str) + "-01", errors='coerce')
    cm_payments = cm_payments[cm_payments['Capacity Payment Suspension Flag'] == 'Not Suspended']
    cm_payments = cm_payments.groupby(DATE_FIELD).agg({'Capacity Payment (£)': 'sum', "Auction Acquired Capacity Obligation (MW)": 'sum'}).reset_index()
    print(cm_payments.head())
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
    create_annual_metric(total_cm_capacity_metric, cm_payments, "Auction Acquired Capacity Obligation (MW)", "mean")
    create_annual_metric(annual_bm_payments_metric, bm_payments, "Total")
    create_monthly_metric(gas_storage_metric, gas_storage, "Gas Reserves (Days)", "mean")
