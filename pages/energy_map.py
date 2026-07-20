import gradio as gr
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from backend.constants import ELEXON_GENERATION_TYPES
import backend.energy_map as energy_map

def _fig_from_error(msg):
    fig = go.Figure()
    fig.update_layout(title=msg)
    return fig

def update_map(time, generator_types):
    if type(time) is float:  # Gradio returns float for datetime, convert to datetime
        time = datetime.fromtimestamp(time)
    fig = energy_map.create_chart(time, generator_types)
    if isinstance(fig, str):
        fig = _fig_from_error(fig)

    return fig

inputs = [
    gr.DateTime(value=datetime.now(), label="Time"), 
    gr.CheckboxGroup(
        choices=[(v, k) for k, v in ELEXON_GENERATION_TYPES.items()], 
        value=list(ELEXON_GENERATION_TYPES.keys()), 
        label="Generator Types")
]

# Energy Map page
with gr.Blocks() as energy_map_page:
    gr.Markdown("## GB Energy Generation Map")
    with gr.Row():
        with gr.Column(scale=3):
            map_plot = gr.Plot(update_map, inputs=inputs)
        with gr.Column(scale=1):
            gr.Markdown("### Filter Options")
            gr.Markdown("Select the time and generator types to filter the data.")
            gr.Markdown("The map shows the locations of generators in Great Britain, with marker sizes proportional to their current generation levels.")
            for i in inputs:
                i.render()
    # for i in inputs:
    #     i.change(update_map, inputs=inputs, outputs=[map_plot])
