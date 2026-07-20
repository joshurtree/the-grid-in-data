import gradio as gr
import pandas as pd
from datetime import datetime, timedelta
from backend.constants import NESO_GENERATION_TYPES
import backend.gbwep as gbwep
import plotly.graph_objects as go

def _fig_from_error(msg):
    fig = go.Figure()
    fig.update_layout(title=msg)
    return fig

def update_chart(start_date, end_date, target, min_usage):
    # chart
    fig = gbwep.filter_daily_data(datetime.fromtimestamp(start_date), datetime.fromtimestamp(end_date), target, min_usage)
    if isinstance(fig, str):
        fig = _fig_from_error(fig)
    fig['Total'] = fig['Total'] / 1000000  # Convert MWh to GWh for color scale
    return fig

def update_table(start_date, end_date, target, min_usage):
    tbl = gbwep.create_table(datetime.fromtimestamp(start_date), datetime.fromtimestamp(end_date), target, min_usage)

    if isinstance(tbl, str):
        tbl = pd.DataFrame({"error": [tbl]})

    return tbl

start_date0 = datetime.now() - timedelta(days=365)
end_date0 = datetime.now()
target0 = list(NESO_GENERATION_TYPES.keys())[0]
min_usage0 = 0
gr.Markdown("## GB Wholesale Electricity Prices")
start_date = gr.DateTime(value=start_date0, label="Start Date", include_time=False)
end_date = gr.DateTime(value=end_date0, label="End Date", include_time=False)
target = gr.Dropdown(
    choices=[(v, k) for k, v in NESO_GENERATION_TYPES.items()],
    value="LOW_CARBON",
    label="Target Generation",
    allow_custom_value=False
)
min_usage = gr.Slider(minimum=0, maximum=100, value=min_usage0, label="Minimum Usage (%)")
inputs = [start_date, end_date, target, min_usage]
# Electricity Prices page
with gr.Blocks() as prices_page:    
    with gr.Row():
        with gr.Column(scale=3):
            gr.Tabs(["Chart", "Table"], elem_id="prices_tabs")
            with gr.Tab("Chart"):
                gr.ScatterPlot(update_chart, x="SettlementDate", y="Price", color="Total", inputs=inputs, label="Electricity Prices")
            with gr.Tab("Table"):
                gr.Dataframe(update_table, inputs=inputs, label="Electricity Prices Table")
        with gr.Column(scale=1):
            gr.Markdown("### Filter Options")
            gr.Markdown("Select the date range, target generation type, and minimum usage percentage to filter the data.")
            gr.Markdown("The chart shows the electricity prices over time, while the table provides detailed statistics for the selected generation type.")
            for i in inputs:
                i.render()
