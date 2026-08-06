import gradio as gr
import pandas as pd
from datetime import datetime, timedelta
from backend.cfd import CFDData, technologies, rounds
import plotly.graph_objects as go
from gradio_datetimerange import DateTimeRange

def create_cfd_chart(date_range, technology, allocation_round):
    cfd_data = CFDData(start_date=date_range[0], end_date=date_range[1], technology=technology, allocation_rounds=allocation_round)
    return cfd_data.create_cfd_chart(), cfd_data.create_strike_price_chart()

date_range = DateTimeRange([datetime.now() - timedelta(days=365), datetime.now()], label="Date Range", include_time=False, type="datetime", quick_ranges=["5y", "1y", "6m", "3m", "1m"])
technology = gr.CheckboxGroup(
    choices=technologies,
    value=technologies,
    label="Technology",
)
allocation_round = gr.CheckboxGroup(
    choices=rounds,
    value=rounds,
    label="Allocation Round"
)
strike_price = gr.Slider(
    label="Strike Price (£/MWh)",
    minimum=0,
    maximum=200,
    value=60,
    step=1
)

# Create Gradio interface
with gr.Blocks(title="Electricity CFD Analysis") as cfd_page:
    gr.Markdown("# Contract for Difference (CFD) Analysis")
    gr.Markdown("Analyze electricity price contracts and CFD payments")
    
    with gr.Tabs():
        with gr.TabItem("CFD by Technology"):
            chart_output = gr.Plot()

        with gr.TabItem("CFD by Strike Price"):
            strike_price_chart_output = gr.Plot()

        with gr.TabItem("List of Contracts"):
            contracts = gr.Dataframe()

    with gr.Sidebar():
        gr.Markdown("### Filter Options")
        gr.Markdown("Select the date range and strike price to analyze the CFD payments.")
        date_range.render()
        technology.render()
        allocation_round.render()

    for i in [date_range, technology, allocation_round]:
        i.change(create_cfd_chart, inputs=[date_range, technology, allocation_round], outputs=[chart_output, strike_price_chart_output])
    cfd_page.load(create_cfd_chart, inputs=[date_range, technology, allocation_round], outputs=[chart_output, strike_price_chart_output])
if __name__ == "__main__":
    demo.launch()