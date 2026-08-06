import gradio as gr
import pandas as pd
from datetime import datetime, timedelta
import backend.elecvsgas as elecvsgas
from backend.constants import PERIOD_GROUPS
from functools import partial

def _fig_from_error(msg):
    fig = go.Figure()
    fig.update_layout(title=msg)
    return fig

def update_chart(func, start_date, end_date, frequency):
    def parse_date(date, default):
        if isinstance(date, float):  # Gradio returns float for datetime, convert to datetime
            return datetime.fromtimestamp(date)
        elif date == None:  # Handle empty string case
            return default
        return date
    start_date = parse_date(start_date, datetime.now() - timedelta(days=365))
    end_date = parse_date(end_date, datetime.now())
    evg_plot = func(start_date, end_date, frequency)

    if isinstance(evg_plot, str):
        return _fig_from_error(f"Error: {evg_plot}")
    else:
        return evg_plot

update_price = partial(update_chart, elecvsgas.create_price_chart)
update_evg = partial(update_chart, elecvsgas.create_chart)
update_ratio = partial(update_chart, elecvsgas.ratio_chart)

# Create partial function for updating the electricity vs gas chart
def update_evg(start_date, end_date, frequency):
    return update_chart(elecvsgas.create_chart, start_date, end_date, frequency)
frequencies = list(PERIOD_GROUPS.keys())[1:]  # Exclude "Hourly" option
start_date0 = datetime(year=2020, month=1, day=1).timestamp()
end_date0 = (datetime.now() + timedelta(days=730)).timestamp()
frequency0 = frequencies[0]  # Default to "Daily"

start_date = gr.DateTime(value=start_date0, label="Start Date", include_time=False)
end_date = gr.DateTime(value=end_date0, label="End Date", include_time=False)

enable_frequency = lambda: gr.Radio(choices=frequencies, value=frequency0, label="Frequency", visible=True)
disable_frequency = lambda: gr.Radio(choices=frequencies, value=frequency0, label="Frequency", visible=False)
frequency = disable_frequency()

# Electricity vs Gas page
with gr.Blocks() as evg_page:
    gr.Markdown("## Gas Prices")
    with gr.Tabs():
        with gr.TabItem("Gas prices (Past and Future)") as gas_prices_tab:
            gr.Markdown(
                """
                This page shows the wholesale gas prices over a specified date range and frequency.
                You can select the start and end dates, as well as the frequency of the data (daily, weekly, or monthly).
                The chart will update automatically based on your selections.
                """
            )
            price_plot = gr.Plot(update_price, inputs=[start_date, end_date, frequency], label="Gas Prices")
            gr.Markdown(
                """
                The gas prices are displayed in pence per kilowatt-hour (p/kWh). The price data for the first day of each month is used for the monthly frequency.
                Past data is sourced from the [ONS](https://www.ons.gov.uk/) and future data is from [Pound Forcast](https://poundf.co.uk/uk-natural-gas).
                Additional verification of forecast using GB Natural Gas Futures data from [ICE](https://www.theice.com/products/279/UK-Natural-Gas-Futures/data?marketId=566&span=1).
                """
            )

        with gr.TabItem("Price Comparison with Electricity") as price_comparison_tab:
            gr.Markdown(
                """
                This page allows you to compare the wholesale electricity and gas prices over a specified date range and frequency.
                You can select the start and end dates, as well as the frequency of the data (daily, weekly, or monthly).
                The chart will update automatically based on your selections.
                """
            )
            evg_plot = gr.Plot(update_evg, inputs=[start_date, end_date, frequency], label="Price Comparison")

        with gr.TabItem("Spark gap (wholesale)") as spark_gap_tab:
            gr.Markdown(
                """
                This tab shows the ratio of electricity price to gas price over time. 
                It provides insights into how the two energy sources compare in terms of cost.
                """
            )
            ratio_plot = gr.Plot(update_ratio, inputs=[start_date, end_date, frequency], label="Electricity/Gas Price Ratio")

    with gr.Sidebar():
        start_date.render()
        end_date.render()
        frequency.render()

        gas_prices_tab.select(disable_frequency, inputs=[], outputs=[frequency])
        price_comparison_tab.select(enable_frequency, inputs=[], outputs=[frequency])
        spark_gap_tab.select(enable_frequency, inputs=[], outputs=[frequency])
