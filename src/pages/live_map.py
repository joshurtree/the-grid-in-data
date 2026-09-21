import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
import plotly.express as px
from backend.constants import ALL_GENERATION_TYPES, ELEXON_GENERATION_TYPES
from backend.energy_map import GenerationData
from src.data.bmrs import fetch_generation_by_type
from zoneinfo import ZoneInfo

def _fig_from_error(msg):
    fig = go.Figure()
    fig.update_layout(title=msg)
    return fig


def update_map(time=None):
    if time is None:
        time = datetime.now(tz=ZoneInfo("Europe/London"))
    energy_map = GenerationData(time)
    fig = energy_map.chart_figure
    if isinstance(fig, str):
        fig = _fig_from_error(fig)

    generation_df = fetch_generation_by_type(time)
    generation_data = px.area(
        generation_df, x="startTime", y=generation_df.columns[1:]
    )
    generation_data.update_layout(
        title="GB Energy Generation by Type",
        xaxis_title="Time",
        yaxis_title="Generation (MW)",
        legend_title="Fuel Type",
    )
    if isinstance(generation_data, str):
        fig = _fig_from_error(generation_data)

    return fig, generation_data, energy_map.monitored


st.markdown("## GB Electricity Generation Map")

map_fig, generation_chart, monitored = update_map()

st.markdown(f"**{monitored}% of generation is monitored**")

st.plotly_chart(map_fig, width='stretch')

st.markdown("### Generator Data")
st.plotly_chart(generation_chart, width='stretch')

st.markdown("### Notes")
st.markdown(
    """
    - The map shows the locations of generators in Great Britain, with marker sizes proportional to their current generation levels.
    - The data is sourced from Elexon and NESO, and may not include all generators.
    - The map is updated every 5 minutes, but the data may be delayed by up to 15 minutes.
    - The map is for informational purposes only and should not be used for trading or investment decisions.
    """
)
