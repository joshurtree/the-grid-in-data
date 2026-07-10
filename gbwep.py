from dataclasses import dataclass
from datetime import datetime, date
import os
import pandas as pd
import plotly.graph_objects as go
from taipy.gui import Gui
import taipy.gui.builder as tgb

from constants import NESO_GENERATION_TYPES, RAW_DATA_DIR, TRANSFORMED_DATA_DIR

base_data: pd.DataFrame = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'half_hourly_data.csv'), parse_dates=['StartTime', 'SettlementDate'])
daily_data: pd.DataFrame = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'daily_data.csv'), parse_dates=['SettlementDate'])
color_range: (int, int) = (daily_data['Total'].min()/1000, daily_data['Total'].max()/1000)
date_range: (datetime, datetime) = (daily_data['SettlementDate'].min(), daily_data['SettlementDate'].max())

# Group by generation type and calculate average price, total generation, and total cost for each generation type
def group_by_generation(start_date, end_date, target_generation, minimum_usage):
    data = filter_data(base_data, start_date, end_date, target_generation, minimum_usage)
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
    return (pd.DataFrame(grouped_data), data[target_generation + '_perc'].max())


def filter_data(data, start_date, end_date, target_generation, minimum_usage):
    print(f'{len(data)} records before filtering')
    filtered_data = data.copy()

    filtered_data = filtered_data[filtered_data['SettlementDate'] >= pd.to_datetime(start_date)]
    filtered_data = filtered_data[filtered_data['SettlementDate'] <= pd.to_datetime(end_date)]
    print(f'{len(filtered_data)} records after date filtering')
    filtered_data = filtered_data[filtered_data[target_generation + '_perc'] >= minimum_usage]

    print(f'{len(filtered_data)} records after filtering by {NESO_GENERATION_TYPES[target_generation]} percentage >= {minimum_usage}%')

    return filtered_data


def create_chart(start_date, end_date, target_generation, minimum_usage):
    data = filter_data(daily_data, start_date, end_date, target_generation, minimum_usage)
    # Create Plotly scatter chart with color by volume
    chart_figure = go.Figure(data=go.Scatter(
        mode='markers',
        x=data['SettlementDate'],
        y=data['Price'],
        marker=dict(
            size=8,
            color=data['Total']/1000,  # Use total generation for color scale
            colorscale='Viridis_r',
            cmin=color_range[0],
            cmax=color_range[1],
            showscale=True,
            colorbar=dict(title=f"Total Generation (GWh)"),
            opacity=0.7,
            line=dict(width=0)
        ),
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Price: £{p:.2f}/MWh<br>{NESO_GENERATION_TYPES[target_generation]}: {r:.1f}%<br>Total Generation: {t:.1f} GWh" 
              for d, p, r, t in zip(data['SettlementDate'], data['Price'], data[target_generation + '_perc'], data['Total']/1000)],
        hovertemplate='%{text}<extra></extra>'
    ))

    chart_figure.update_yaxes(range=[0, 450])  # Fix y-axis max to max price for better comparison     
    chart_figure.update_layout(
        title='Wholesale Price vs Date',
        xaxis_title='Date',
        yaxis_title='Price (£/MWh)',
        hovermode='closest',
        template='plotly_dark',
        height=600
    )

    return (chart_figure, data[target_generation + '_perc'].max())

target_generation: str = "LOW_CARBON"
minimum_usage: int = 0
start_date: date = date.today() - pd.DateOffset(years=1)  # Default to one year ago
end_date: date = date.today()
date_range = [start_date, end_date]
show_table: bool = False
maximum_usage: int = 100
(chart_figure, maximum_usage) = create_chart(start_date, end_date, target_generation, minimum_usage)
(table, maximum_usage) = group_by_generation(start_date, end_date, target_generation, minimum_usage)

def update_chart(state):
    if not state.show_table:
        (state.chart_figure, state.maximum_usage) = create_chart(state.date_range[0], state.date_range[1], state.target_generation, state.minimum_usage)
    else:
        (state.table, state.maximum_usage) = group_by_generation(state.date_range[0], state.date_range[1], state.target_generation, state.minimum_usage)
    
with tgb.Page() as gbwep_page:
    tgb.text(value="# GB Electricity Prices", mode="md")
    with tgb.part(class_name="card"):
        tgb.selector("{target_generation}", label="Target Generation Type", lov=list(NESO_GENERATION_TYPES.items()), on_change=update_chart, dropdown=True)
        with tgb.layout(columns="2 1"):
            # with tgb.part():
            #     tgb.date("{start_date}", label="Start Date", min=date(2016, 6, 30), max=date.today(), format='dd/MM/yyyy', on_change=update_chart, layout=tgb.layout(width="20%"))
            # with tgb.part():
            #     tgb.date("{end_date}", label="End Date", min=date(2016, 6, 30), max=date.today(), format='dd/MM/yyyy', on_change=update_chart, layout=tgb.layout(width="20%"))
            with tgb.part():
                tgb.date_range("{date_range}", label="Date Range", min=date(2016, 6, 30), max=date.today(), format='dd/MM/yyyy', on_change=update_chart, layout=tgb.layout(width="40%"))
            with tgb.part():
                tgb.toggle(value="{show_table}", label="Show Table", on_change=update_chart)
        with tgb.layout(columns="1 3"):
            with tgb.part():
                tgb.text(value=f"Filter by minimum target generation (%)", mode="md")
            with tgb.part():
                tgb.slider("{minimum_usage}", label=f"Minimum target generation (%)", min=0, max="{maximum_usage}", on_change=update_chart, layout=tgb.layout(width="40%"))                
    with tgb.part(class_name="card"):
        with tgb.part(render="{not show_table}"):
            tgb.chart(figure="{chart_figure}", title=f"Wholesale Price vs Date", xaxis_title="Date", yaxis_title="Price (£/MWh)", hovermode="closest", template="plotly_dark")
        with tgb.part(render="{show_table}"):
            tgb.table("{table}", title="Average Generation by Price Group", columns=table.columns.tolist(), number_format="%.2f", show_all=True)
    with tgb.part(class_name="card"):
        tgb.text(value="## Notes", mode="md")
        tgb.text(value="- Generation data is sourced from [Neso](https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/resource/f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv).", mode="md")
        tgb.text(value="- Price data is sourced from the [Low Carbon Contracts Company](https://dp.lowcarboncontracts.uk/dataset/19f1ebee-93b7-4ef4-9465-bba50fa4ad06/resource/866e6a4e-86c7-411e-9464-2ac3ad56ae35/download/imrp_actuals.csv).", mode="md")
        tgb.text(value="- Chart inspired by [Ember](https://ember-energy.org/latest-insights/british-power-prices-are-increasingly-independent-from-gas/).", mode="md")
        tgb.text(value="- The chart shows the average wholesale price per day, colored by the percentage of the selected generation type.", mode="md")
        tgb.text(value="- The table below shows the average generation and cost for each generation type over the selected date range.", mode="md")
        
