import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import backend.elecvsgas as elecvsgas
from backend.constants import FREQ_GROUPS
from datasources.supply import current_gas_price_metric, total_gas_cost_metric, sparkgap_metric
from pages.base import display_chart, date_range_slider, display_metrics, footer

st.markdown("## Gas Prices")

frequencies = list(FREQ_GROUPS.keys())[1:]  # Exclude "Hourly" option

with st.sidebar:
    st.markdown("### Filter Options")

    start_date, end_date, frequency = date_range_slider(date(year=2020, month=1, day=1), date.today() + timedelta(days=365*2), frequency_options=list(FREQ_GROUPS.keys())[1:], key_prefix="gas_price")
    
    gas_usage = st.slider(
        "Gas Usage (%)",
        min_value=0,
        max_value=100,
        value=[0, 100],
        key="gas_usage"
    )

start_dt = datetime.combine(start_date, datetime.min.time())
end_dt = datetime.combine(end_date, datetime.min.time())

display_metrics([current_gas_price_metric, total_gas_cost_metric, sparkgap_metric])

st.markdown(
    """
    Gas prices are a critical component of the energy market in Great Britain, influencing both electricity prices and the overall cost of energy for 
    consumers and businesses.
    This dashboard provides insights into the wholesale electricity and gas prices in Great Britain.
    You can explore the historical and forecasted prices, compare electricity and gas prices, and analyze the ratio of electricity to gas prices over time.
    Use the sidebar to filter the data by date range and frequency.
    """
)

display_chart(elecvsgas.create_price_chart(start_dt, end_dt, period_group=frequency, gas_usage=gas_usage))
ratio = st.toggle("Show Ratio of Electricity to Gas Prices", key="show_ratio")
display_chart(elecvsgas.create_chart(start_dt, end_dt, period_group=frequency, gas_usage=gas_usage, as_ratio=ratio))
footer()