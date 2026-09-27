from dataclasses import dataclass
from datetime import datetime, date
import os
from typing import Tuple
import pandas as pd
import plotly.graph_objects as go

from constants import FREQ_GROUPS, NESO_GENERATION_TYPES
from  datasources.system import half_hourly_dataset, daily_dataset
from .chartset import Chart

def filter_data(data: pd.DataFrame, start_date: date, end_date: date, target_generation: str, usage: tuple[float, float]) -> Tuple[pd.DataFrame, float]:
    print(f'{len(data)} records before filtering')
    filtered_data = data.copy()
    
    print(f'Filtering data from {start_date} to {end_date} for {target_generation} with minimum usage of {usage[0]}% and maximum usage of {usage[1]}%')
    filtered_data = filtered_data[filtered_data['Settlement Date'] >= pd.to_datetime(start_date)]
    filtered_data = filtered_data[filtered_data['Settlement Date'] <= pd.to_datetime(end_date)]
    y_max = filtered_data['Price'].max() * 1.1  # Set a fixed maximum for the y-axis to allow better scaling
    print(f'{len(filtered_data)} records after date filtering')
    y_max = filtered_data['Price'].max() * 1.1  # Set a fixed maximum for the y-axis to allow better scaling
    filtered_data = filtered_data[filtered_data[target_generation + ' (%)'] >= usage[0]]
    filtered_data = filtered_data[filtered_data[target_generation + ' (%)'] <= usage[1]]

    print(f'{len(filtered_data)} records after filtering by {target_generation} percentage >= {usage[0]}% and <= {usage[1]}%')
    return filtered_data, y_max

def create_chart(start_date: date, end_date: date, frequency: str, target_generation: str|None, usage: tuple[float, float]) -> Chart:
    target_generation = target_generation or "Low Carbon"  # Default to Low Carbon if None    
    filtered_data, y_max = filter_data(daily_dataset.load_data(), start_date, end_date, target_generation, usage)
    data = filtered_data.rolling(FREQ_GROUPS.get(frequency, 'D'), on='Settlement Date').mean().reset_index()  # Resample to daily frequency for better visualization
    if data.empty:
        # Handle the case where there is insufficient data to create a chart
        chart_figure = go.Figure()
        chart_figure.add_annotation(
            text="No Data.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
    else:
        data["Description"] = data.apply(lambda row: f"Date: {row['Settlement Date'].strftime('%d %B %Y')}<br>Price: £{row['Price']:.2f}/MWh<br>{target_generation}: {row[target_generation + ' (%)']:.1f}%<br>Total Generation: {row['Total'] / 1000:.1f} GWh", axis=1)
        # Create Plotly scatter chart with color by volume
        chart_figure = go.Figure(data=go.Scatter(
            mode='markers',
            x=data['Settlement Date'],
            y=data['Price'],
            marker=dict(
                size=8,
                color=data[target_generation + ' (%)'],
                colorscale='turbo',
                showscale=True,
                colorbar=dict(title=f"Usage (%)"),
                opacity=0.7,
                line=dict(width=0)
            ),
            text=data['Description'],
            hovertemplate='%{text}<extra></extra>'
        ))

        chart_figure.update_yaxes(range=[0, y_max])  # Fix y-axis max to max price for better comparison

    chart_figure.update_layout(
        xaxis_title='Date',
        yaxis_title='Price (£/MWh)',
        hovermode='closest',
    )

    return Chart(
        half_hourly_dataset, 
        filtered_data, 
        chart_figure, 
        title="Wholesale Price and Generation Mix", 
        description="This chart shows the relationship between wholesale electricity prices and generation types over time.")

# Group by generation type and calculate average price, total generation, and total cost for each generation type
def create_table(start_date: date, end_date: date, target_generation: str|None, usage: tuple[float, float]) -> Chart:
    target_generation = target_generation or "Low Carbon"  # Default to Low Carbon if None
    data, _ = filter_data(half_hourly_dataset.load_data(), start_date, end_date, target_generation, usage)

    def calc_data(gen_type):
        if data[gen_type].sum() < data['Total'].sum() * 0.001:  # Skip groups that contribute less than 0.1% of total generation
            return None

        avg_price = (data['Price'] * data[gen_type]).sum() / data[gen_type].sum() if data[gen_type].sum() > 0 else 0
        total_generation = data[gen_type].sum()
        total_cost = (data['Price'] * data[gen_type]).sum()
        return {
            'Generation type': gen_type,
            'Percentage of Total Generation (%)': (data[gen_type].sum() / data['Total'].sum()) * 100 if data['Total'].sum() > 0 else 0,
            'Average next day price (£/MWh)': avg_price,
            'Total generated (GWh)': total_generation / 1000,  # Convert MWh to GWh
            'Total cost (£ million)': total_cost / 1e6  # Convert £ to £ million
        }

    grouped_data = [calc_data(gen_type) for gen_type in NESO_GENERATION_TYPES.values() if calc_data(gen_type) is not None]
    grouped_data.append({
        'Generation type': 'total',
        'Percentage of Total Generation (%)': 100,
        'Average next day price (£/MWh)': (data['Price'] * data['Total']).sum() / data['Total'].sum() if data['Total'].sum() > 0 else 0,
        'Total generated (GWh)': data['Total'].sum() / 1000,  # Convert MWh to GWh
        'Total cost (£ million)': (data['Price'] * data['Total']).sum() / 1e6  # Convert £ to £ million
    })  # Add total row

    return Chart(
        half_hourly_dataset, 
        pd.DataFrame(grouped_data), 
        title="Wholesale Price vs Date", 
        description="This chart shows the relationship between wholesale electricity prices and generation types over time.")