from datetime import datetime, timezone
import json
import os
import pandas as pd
import plotly.graph_objects as go
from backend.constants import ELEXON_GENERATION_TYPES, GENERATION_COLOURS, GENERATION_TYPE_GROUPS, GENERATION_SUPER_GROUPS, TRANSFORMED_DATA_DIR
from backend.bmrs import fetch_FPN
from backend.geojson import add_boundaries_to_chart

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
    print(f"[DEBUG] Creating data with time={time}, generator_types={generator_types}")
    generation = fetch_FPN(time if time else datetime.now())
    print(f"[DEBUG] Fetched {len(generation)} generation records")
    data = pd.DataFrame([create_scatter_data(row, generation) for _, row in generators.iterrows()])
    
    data = data[data['current_generation'] > 0]  # Filter out generators with zero current generation
    data = data[data['fuel_type'].isin(generator_types)]  # Filter by selected generator types

    # Safe construction of the hover text column (avoid DataFrame-from-apply issues)
    if data.empty:
        data['text'] = []
    else:
        # Resolve human-readable fuel type names, fallback to the raw fuel type key
        fuel_labels = data['fuel_type'].map(lambda ft: ELEXON_GENERATION_TYPES.get(ft, ft))
        # Build the text column vectorized
        data['text'] = (
            data['name'].astype(str)
            + " ("
            + fuel_labels.astype(str)
            + "): "
            + data['current_generation'].map(lambda v: f"{v:.2f}")
            + " MW"
        )

    print(f"[DEBUG] Created data with {len(data)} generators after filtering")
    return data

def create_chart(time, generator_types):
    data = create_data(time, generator_types)
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

