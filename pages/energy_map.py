import gradio as gr
import pandas as pd
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
from backend.constants import ELEXON_GENERATION_TYPES
import backend.energy_map as energy_map

def _fig_from_error(msg):
    fig = go.Figure()
    fig.update_layout(title=msg)
    return fig

def update_map(time):
    if type(time) is float:  # Gradio returns float for datetime, convert to datetime
        time = datetime.fromtimestamp(time, tz=timezone.utc)
    fig, monitored = energy_map.create_chart(time)
    if isinstance(fig, str):
        fig = _fig_from_error(fig)
    return fig, monitored


# Energy Map page
with gr.Blocks() as energy_map_page:
    gr.Markdown("## GB Energy Generation Map")
    with gr.Row():
        monitored = gr.HTML(value=0, html_template="{{value}}% of generation is monitored")
    with gr.Row():
        with gr.Column(scale=3):
            map_plot = gr.Plot()
        with gr.Column(scale=1):
            gr.Markdown("### Filter Options")
            gr.Markdown("Select the time and generator types to filter the data.")
            gr.Markdown("The map shows the locations of generators in Great Britain, with marker sizes proportional to their current generation levels.")
            inputs = [
                gr.DateTime(value=datetime.now(), label="Time"), 
            ]
    update_map(datetime.now(timezone.utc))  # Initial update
    for i in inputs:
        i.change(update_map, inputs=inputs, outputs=[map_plot, monitored])