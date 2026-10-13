import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from .chartset import AreaTrace, Chart, ChartBuilder, Trace, LineTrace
from datasources.system import supply_vs_demand_dataset
from constants import DATE_FIELD, DATETIME_FIELD, FREQ_GROUPS, NESO_GENERATION_TYPES

supply_traces = [AreaTrace(name, stackgroup="supply") for name in ['Coal', 'Storage', 'Nuclear', 'Imports', 'Gas', 'Wind', 'Embedded Wind', 'Solar', 'Biomass', 'Hydro', 'Other']]
demand_traces = [AreaTrace(name, stackgroup="demand") for name in ['Storage Load', 'Transmission Losses', 'Station Load', 'Exports', 'National Demand']] + [LineTrace('Transmission System Demand', kwargs=dict(line_color='black', line_width=2, line_dash='dash'))]

def create_supply_vs_demand_chart(start_date, end_date, frequency):
    # Load the data
    df = supply_vs_demand_dataset.load_data()
    def filter_data(df):
        # Filter the data based on the selected date range
        df = df[(df[DATETIME_FIELD] >= pd.to_datetime(start_date.tz_localize('utc'))) & (df[DATETIME_FIELD] <= pd.to_datetime(end_date.tz_localize('utc')))]
        return df

    # Filter the data based on the selected date range
    builder = ChartBuilder(
        supply_vs_demand_dataset,
        filter_functions=[
            filter_data,
            lambda df: df.resample(FREQ_GROUPS[frequency], on=DATETIME_FIELD).mean().interpolate().reset_index()
        ],
        title="Supply vs Demand",
        description="This chart shows the supply and demand of electricity in the UK over time, allowing for analysis of how supply meets demand."
    )

    chart = builder.create_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0, specs=[[{"type": "scatter"}], [{"type": "scatter"}]])
    builder.add_traces(chart.chart, chart.table, DATETIME_FIELD, demand_traces, row=2, col=1)
    builder.add_traces(chart.chart, chart.table, DATETIME_FIELD, supply_traces, row=1, col=1)
    return chart