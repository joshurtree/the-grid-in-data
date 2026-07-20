import gradio as gr
import pandas as pd
from datetime import datetime, timedelta
import backend.elecvsgas as elecvsgas

def _fig_from_error(msg):
    fig = go.Figure()
    fig.update_layout(title=msg)
    return fig

def update_evg(start_date, end_date, frequency):
    evg_plot = elecvsgas.create_chart(datetime.fromtimestamp(start_date), datetime.fromtimestamp(end_date), frequency)

    if isinstance(evg_plot, str):
        return _fig_from_error(f"Error: {evg_plot}")
    else:
        return evg_plot

start_date0 = (datetime.now() - timedelta(days=365)).timestamp()
end_date0 = datetime.now().timestamp()
frequency0 = "Daily"
fig0 = update_evg(start_date0, end_date0, frequency0)

# Electricity vs Gas page
with gr.Blocks() as evg_page:
    gr.Markdown("## Electricity vs Gas Prices")
    with gr.Row():
        with gr.Column(scale=3):
            evg_plot = gr.Plot(fig0, label="Price Comparison")

        with gr.Column(scale=1):
            evg_start = gr.DateTime(value=start_date0, label="Start Date", include_time=False)
            evg_end = gr.DateTime(value=end_date0, label="End Date", include_time=False)
            evg_frequency = gr.Radio(choices=["Daily", "Weekly", "Monthly"], value=frequency0, label="Frequency")

    inputs = [evg_start, evg_end, evg_frequency]
    outputs = [evg_plot]
    for inp in inputs:
        inp.change(update_evg, inputs=inputs, outputs=outputs)
