import gradio as gr
import pandas as pd
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
import plotly.express as px
from backend.constants import ALL_GENERATION_TYPES, ELEXON_GENERATION_TYPES
from backend.energy_map import GenerationData
from backend.bmrs import fetch_generation_by_type
from zoneinfo import ZoneInfo

def _fig_from_error(msg):
    fig = go.Figure()
    fig.update_layout(title=msg)
    return fig

def update_map(time = datetime.now(tz=ZoneInfo("Europe/London"))):
    if type(time) is float:  # Gradio returns float for datetime, convert to datetime
        time = datetime.fromtimestamp(time, tz=ZoneInfo("Europe/London"))
    energy_map = GenerationData(time)
    fig = energy_map.chart_figure
    if isinstance(fig, str):
        fig = _fig_from_error(fig)

    layout = go.Layout(
        title="GB Energy Generation by Type",
        xaxis_title="Time",
        yaxis_title="Generation (MW)",
        barmode='stack',
        legend_title="Fuel Type",
    )
    generation_data = px.area(fetch_generation_by_type(), x="startTime", y=list(ELEXON_GENERATION_TYPES.keys()))
    if isinstance(generation_data, str):
        fig = _fig_from_error(generation_data)
    return fig, generation_data, energy_map.monitored


# Energy Map page
with gr.Blocks() as energy_map_page:
    gr.Markdown("## GB Energy Generation Map")
    with gr.Row():
        monitored = gr.HTML(value=0, html_template="{{value}}% of generation is monitored")
    with gr.Row():
        with gr.Column(scale=3):
            map_plot = gr.Plot()
        with gr.Column(scale=1):
            gr.Markdown("### Generator Data")
    with gr.Row():
        generation_chart = gr.Plot()

    with gr.Row():
        gr.Markdown("### Notes")
        gr.Markdown(
            """
            - The map shows the locations of generators in Great Britain, with marker sizes proportional to their current generation levels.
            - The data is sourced from Elexon and NESO, and may not include all generators.
            - The map is updated every 5 minutes, but the data may be delayed by up to 15 minutes.
            - The map is for informational purposes only and should not be used for trading or investment decisions.
            """
        )
    update_map(datetime.now(tz=ZoneInfo("Europe/London")))  # Initial update
    energy_map_page.load(update_map, outputs=[map_plot, generation_chart, monitored])
    # for i in inputs:
    #     i.change(update_map, inputs=inputs, outputs=[map_plot, generation_chart, monitored])