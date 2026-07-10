from datetime import datetime, timezone
import json
import os
import pandas as pd
import plotly.graph_objects as go
import taipy.gui.builder as tgb
from constants import ELEXON_GENERATION_TYPES, GENERATION_COLOURS, GENERATION_TYPE_GROUPS, GENERATION_SUPER_GROUPS, TRANSFORMED_DATA_DIR
from bmrs import fetch_FPN
from geojson import add_boundaries_to_chart

generators = pd.read_json(os.path.join(TRANSFORMED_DATA_DIR, 'all_generators.json'))

# GENERATION_TYPES = [
#     ('FOSSIL', 'Fossil fuels', [
#         ('GAS', 'Gas' ),
#     ]),
#     ('LOW_CARBON', 'Low carbon generation', [
#         ('NUCLEAR', 'Nuclear'),
#         ('WIND', 'Wind'),
#         ('WIND_EMB', 'Wind (Embedded)'),
#         ('HYDRO', 'Hydro'),
#         ('SOLAR', 'Solar'),
#     ]),
#     ('Other', 'Other generation types', [
#         ('IMPORTS', 'Imports'),
#         ('BIOMASS', 'Biomass'),
#         ('OTHER', 'Other'),
#         ('STORAGE', 'Storage'),
#     ])
# ]

#def embeded_generation(row, time):
    

def aggregate_generation(rows, time):
    total_generation = 0
    rows = rows[pd.to_datetime(rows['timeFrom'], utc=True) <= time]
    rows = rows[pd.to_datetime(rows['timeTo'], utc=True) >= time]

    for _, row in rows.iterrows():
        # Interpolate the generation level based on the time within the range
        time_from = pd.to_datetime(row["timeFrom"], utc=True)
        time_to = pd.to_datetime(row["timeTo"], utc=True)
        total_duration = (time_to - time_from).total_seconds()
        elapsed_duration = (time - time_from).total_seconds()
        if total_duration > 0:
            interpolated_level = row["levelFrom"] + (row["levelTo"] - row["levelFrom"]) * (elapsed_duration / total_duration)
            total_generation += max(interpolated_level, 0)
    return total_generation


def get_generation(bmus):
    if not bmus.empty:
        return aggregate_generation(bmus, datetime.now(timezone.utc))
    return 0

def create_scatter_data(row, generation):
    unit_generation = get_generation(generation[generation['bmUnit'].isin(row['elexonBmUnit'])])
    return {
        "name": row["Site Name"],
        "fuel_type": row["fuelType"],
        "lat": row["Latitude"],
        "lon": row["Longitude"],
        "colour": GENERATION_COLOURS.get(row['fuelType'], '#FF0000'),
        "current_generation": unit_generation
    }

def create_data(time, generator_types):
    global data
    print(f"[DEBUG] Creating data with time={time}, generator_types={generator_types}")
    generation = fetch_FPN(time if time else datetime.now())
    print(f"[DEBUG] Fetched {len(generation)} generation records")
    data = pd.DataFrame([create_scatter_data(row, generation) for _, row in generators.iterrows()])
    data = data[data['current_generation'] > 0]  # Filter out generators with zero current generation
    data = data[data['fuel_type'].isin(generator_types)]  # Filter by selected generator types
    data['text'] = data.apply(lambda row: f"{row['name']} ({ELEXON_GENERATION_TYPES[row['fuel_type']]}): {row['current_generation']:.2f} MW", axis=1)
    print(f"[DEBUG] Created data with {len(data)} generators after filtering")
    return data

def update_chart(data):
    # Create Plotly figure with boundaries and generator markers
    chart_figure = go.Figure()

    # Add boundaries
    add_boundaries_to_chart(chart_figure, 'data/ETYS-boundaries-simple.geojson', "Boundary_n")

    # Add generator markers
    chart_figure.add_trace(go.Scattergeo(
        lon=data['lon'],
        lat=data['lat'],
        mode='markers',
        marker=dict(size=data['current_generation'] / 10, color=data['colour'], opacity=0.5),
        text=data["text"],
        hovertemplate='%{text}<extra></extra>',
        name='Generators'
    ))
    chart_figure.update_geos(
        scope='europe',
        projection_type='mercator',
        resolution=50,
        showland=True,
        showocean=True,
        landcolor='rgb(74, 170, 68)',
        oceancolor='rgb(119, 221, 221)',
        lataxis=dict(range=[49.5, 61.5]),
        lonaxis=dict(range=[-8, 3])
    )

    # Add legend for fuel types
    for group in GENERATION_TYPE_GROUPS:
        chart_figure.add_trace(go.Scattergeo(
            lon=[None],  # Dummy data for legend
            lat=[None],
            mode='markers',
            marker=dict(size=10, color=group['colour']),
            name=group['label']
        ))

    # Update layout
    chart_figure.update_layout(
        title='GB Generation Live Map',
        height=1200,
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode='closest'
    )

    return chart_figure

def do_update_chart(state):
    data = create_data(state.time, state.fossil_fuel_types + state.low_carbon_types + state.other_types)
    state.chart_figure = update_chart(data)

def do_show_generator_details(state):
    if len(state.selected_generator) == 0:
        return
    generator_info = state.data.iloc[state.selected_generator[-1]].to_dict('records')[0]
    state.generator_details = f"## {generator_info['name']}\n"
    state.generator_details += f"| **Fuel Type** | {ELEXON_GENERATION_TYPES[generator_info['fuel_type']]} |\n"
    state.generator_details += f"| **Latitude** | {generator_info['lat']} |\n"
    state.generator_details += f"| **Longitude** | {generator_info['lon']} |\n"
    state.generator_details += f"| **Current Generation** | {generator_info['current_generation']:.2f} MW |\n"
    #state.generator_details += f"**BMU IDs: {', '.join(generator_info['elexonBmUnit'])}\n"
    state.show_generator_details = True

fossil_fuel_types = GENERATION_SUPER_GROUPS['Fossil Fuels']
low_carbon_types = GENERATION_SUPER_GROUPS['Low Carbon']
other_types = GENERATION_SUPER_GROUPS['Other'] 
selected_generator = []
generator_details = ""
show_generator_details = False
time = datetime.now()
data = create_data(time, fossil_fuel_types + low_carbon_types + other_types)
chart_figure = update_chart(data)

def get_generator_types(group):
    return [(fuel_type, ELEXON_GENERATION_TYPES[fuel_type]) for fuel_type in GENERATION_SUPER_GROUPS[group]]

with tgb.Page() as generation_map:
    with tgb.part(class_name="card"):
        tgb.text(value="# GB Generation Live Map", mode="md")
        with tgb.layout(columns="1 1"):
            with tgb.part():
                tgb.text(value="### Total Generators: {len(data)}", mode="md")
            with tgb.part(): 
                tgb.text(value="### Total Tracked Generation: {int(data['current_generation'].sum())} MW", mode="md")

    with tgb.part(class_name="card"):
            tgb.chart(figure="{chart_figure}", scale="4.0", on_change="do_show_generator_details", selected="{selected_generator}")
            with tgb.expandable("Generator Information", expand="{show_generator_details}"):
                tgb.text(value="{generator_details}", mode="md")
    with tgb.part(class_name="card"):
        tgb.date("{time}", label="Date/Time", with_time=True, on_change="do_update_chart")
        with tgb.layout(columns="1 1 1"):
            with tgb.part():
                tgb.selector("{fossil_fuel_types}", label='Fossil Fuels', show_select_all=True, lov=get_generator_types('Fossil Fuels'), on_change="do_update_chart", multiple=True)
            with tgb.part():
                tgb.selector("{low_carbon_types}", label='Low Carbon', show_select_all=True, lov=get_generator_types('Low Carbon'), on_change="do_update_chart", multiple=True)
            with tgb.part():
                tgb.selector("{other_types}", label='Other', show_select_all=True, lov=get_generator_types('Other'), on_change="do_update_chart", multiple=True)
