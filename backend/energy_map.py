from datetime import datetime, timezone
import json
import os
import pandas as pd
import plotly.graph_objects as go
from backend.constants import ELEXON_GENERATION_TYPES, GENERATION_COLOURS, GENERATION_TYPE_GROUPS, GENERATION_SUPER_GROUPS, TRANSFORMED_DATA_DIR
from backend.bmrs import fetch_FPN, time_to_settlement_period
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

def current_generation(row, time):
    # Interpolate the generation level based on the time within the range
    time_from = pd.to_datetime(row["timeFrom"], utc=True)
    time_to = pd.to_datetime(row["timeTo"], utc=True)
    total_duration = (time_to - time_from).total_seconds()
    elapsed_duration = (time - time_from).total_seconds()
    return row["levelFrom"] + (row["levelTo"] - row["levelFrom"]) * (elapsed_duration / total_duration)

def aggregate_generation(rows, time):
    total_generation = 0
    rows = rows[pd.to_datetime(rows['timeFrom'], utc=True) <= time]
    rows = rows[pd.to_datetime(rows['timeTo'], utc=True) >= time]

    for _, row in rows.iterrows():
        total_generation += row['level']

    return total_generation

def get_embedded_generation(time):
    generation = pd.read_csv(os.path.join(RAW_DATA_DIR, 'embedded_generation.csv'))
    return generation[generation['SETTLEMENT_DATE'] == time.strftime('%Y-%m-%dT00:00:00') and (generation['SETTLEMENT_PERIOD'] == time_to_settlement_period(time))]

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
        "level": unit_generation
    }

def create_data(time, show_generation=True):
    print(f"[DEBUG] Creating data with time={time}, show_generation={show_generation}")
    fpn = fetch_FPN(time if time else datetime.now())
    fpn['level'] = fpn.apply(lambda row: current_generation(row, time), axis=1)
    fpn = fpn[fpn['level'] > 0] if show_generation else fpn[fpn['level'] < 0]
    print(f"[DEBUG] Fetched {len(fpn)} generation records")
    data = pd.DataFrame([create_scatter_data(row, fpn) for _, row in generators.iterrows()])

    monitored = round(data['level'].sum() / fpn['level'].sum() * 100, 2) if not data.empty else 0
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
            + data['level'].map(lambda v: f"{v:.2f}")
            + " MW"
        )

    print(f"[DEBUG] Created data with {len(data)} generators after filtering")
    return data, monitored,

def create_chart(time, show_generation=True):
    data, monitored = create_data(time, show_generation)
    config = {
        'displayModeBar': False,
        'displaylogo': False,
    }
    # Create Plotly figure with boundaries and generator markers
    chart_figure = go.Figure()

    # Add boundaries
    add_boundaries_to_chart(chart_figure, 'data/ETYS-boundaries-simple.geojson', "Boundary_n")

    for group in ELEXON_GENERATION_TYPES.keys():
        trace_data = data[data['fuel_type'] == group]
        if not trace_data.empty: 
            chart_figure.add_trace(go.Scattergeo(
                lon=trace_data['lon'],
                lat=trace_data['lat'],
                mode='markers',
                marker=dict(size=trace_data['level'] / 10, color=trace_data['colour'], opacity=0.5),
                text=trace_data["text"],
                hovertemplate='%{text}<extra></extra>',
                name=ELEXON_GENERATION_TYPES[group]
            ))
    chart_figure.update_geos(
        scope='europe',
        projection_type='mercator',
        resolution=50,
        showland=True,
        showocean=True,
        landcolor='rgb(74, 170, 68)',
        oceancolor='rgb(119, 221, 221)',
        # lataxis=dict(range=[54, 60]),
        # lonaxis=dict(range=[-8, 3.5]),
        fitbounds='locations'
    )

    # Update layout
    chart_figure.update_layout(
        title='GB Generation Live Map',
        height=1200,
        hovermode='closest'
    )

    return chart_figure, monitored

