from dataclasses import dataclass
from datetime import datetime, date
import os
from typing import Tuple
import pandas as pd
import plotly.graph_objects as go

from backend.constants import NESO_GENERATION_TYPES, RAW_DATA_DIR, TRANSFORMED_DATA_DIR

base_data: pd.DataFrame = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'half_hourly_data.csv'), parse_dates=['StartTime', 'SettlementDate'])
daily_data: pd.DataFrame = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'daily_data.csv'), parse_dates=['SettlementDate'])
color_range: Tuple[int, int] = (daily_data['Total'].min()/1000, daily_data['Total'].max()/1000)

# Group by generation type and calculate average price, total generation, and total cost for each generation type
def create_table(start_date: datetime, end_date: datetime, target_generation: str, minimum_usage: float):
    data, y_max = filter_data(base_data, start_date, end_date, target_generation, minimum_usage)
    def calc_data(gen_type):
        if data[gen_type].sum() < data['Total'].sum() * 0.001:  # Skip groups that contribute less than 0.1% of total generation
            return None

        avg_price = (data['Price'] * data[gen_type]).sum() / data[gen_type].sum() if data[gen_type].sum() > 0 else 0
        total_generation = data[gen_type].sum()
        total_cost = (data['Price'] * data[gen_type]).sum()
        return {
            'Generation type': NESO_GENERATION_TYPES[gen_type],
            'Percentage of Total Generation (%)': (data[gen_type].sum() / data['Total'].sum()) * 100 if data['Total'].sum() > 0 else 0,
            'Average next day price (£/MWh)': avg_price,
            'Total generated (GWh)': total_generation/1000,  # Convert MWh to GWh
            'Total cost (£ million)': total_cost/1e6  # Convert £ to £ million
        }

    grouped_data = [calc_data(gen_type) for gen_type in NESO_GENERATION_TYPES.keys() if calc_data(gen_type) is not None]
    grouped_data.append({
            'Generation type': 'Total',
            'Percentage of Total Generation (%)': 100,
            'Average next day price (£/MWh)': (data['Price'] * data['Total']).sum() / data['Total'].sum() if data['Total'].sum() > 0 else 0,
            'Total generated (GWh)': data['Total'].sum()/1000,  # Convert MWh to GWh
            'Total cost (£ million)': (data['Price'] * data['Total']).sum()/1e6  # Convert £ to £ million
    })  # Add total row
    return pd.DataFrame(grouped_data)


def filter_data(data: pd.DataFrame, start_date: datetime, end_date: datetime, target_generation: str, usage: [float, float]):
    print(f'{len(data)} records before filtering')
    filtered_data = data.copy()

    print(f'Filtering data from {start_date} to {end_date} for {NESO_GENERATION_TYPES[target_generation]} with minimum usage of {usage[0]}% and maximum usage of {usage[1]}%')
    filtered_data = filtered_data[filtered_data['SettlementDate'] >= pd.to_datetime(start_date)]
    filtered_data = filtered_data[filtered_data['SettlementDate'] <= pd.to_datetime(end_date)]
    y_max = filtered_data['Price'].max() * 1.1  # Set a fixed maximum for the y-axis to allow better scaling
    print(f'{len(filtered_data)} records after date filtering')
    filtered_data = filtered_data[filtered_data[target_generation + '_perc'] >= usage[0]]
    filtered_data = filtered_data[filtered_data[target_generation + '_perc'] <= usage[1]]

    print(f'{len(filtered_data)} records after filtering by {NESO_GENERATION_TYPES[target_generation]} percentage >= {usage[0]}% and <= {usage[1]}%')

    return filtered_data, y_max

def filter_daily_data(start_date: datetime, end_date: datetime, target_generation: str, usage: [float, float]):
    return filter_data(daily_data, start_date, end_date, target_generation, usage)

def create_chart(start_date: datetime, end_date: datetime, target_generation: str, usage: [float, float]):
    data, y_max = filter_data(daily_data, start_date, end_date, target_generation, usage)
    # Create Plotly scatter chart with color by volume
    chart_figure = go.Figure(data=go.Scatter(
        mode='markers',
        x=data['SettlementDate'],
        y=data['Price'],
        marker=dict(
            size=8,
            color=data[target_generation + '_perc']*100, 
            colorscale='Viridis_r',
            showscale=True,
            colorbar=dict(title=f"Usage (%)"),
            opacity=0.7,
            line=dict(width=0)
        ),
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Price: £{p:.2f}/MWh<br>{NESO_GENERATION_TYPES[target_generation]}: {r:.1f}%<br>Total Generation: {t:.1f} GWh" 
              for d, p, r, t in zip(data['SettlementDate'], data['Price'], data[target_generation + '_perc'], data['Total']/1000)],
        hovertemplate='%{text}<extra></extra>'
    ))

    chart_figure.update_yaxes(range=[0, y_max])  # Fix y-axis max to max price for better comparison
    chart_figure.update_layout(
        title='Wholesale Price vs Date',
        xaxis_title='Date',
        yaxis_title='Price (£/MWh)',
        hovermode='closest',
        template='plotly_dark',
        height=600
    )

    return chart_figure

