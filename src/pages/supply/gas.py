import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import figures.elecvsgas as elecvsgas
import figures.gas as gas
from constants import FREQ_GROUPS
from  datasources.supply import current_gas_price_metric, total_gas_cost_metric, gas_storage_metric
from pages.base import display_chart, date_range_slider, display_metrics, footer

st.markdown("## Gas Prices")

frequencies = list(FREQ_GROUPS.keys())[1:]  # Exclude "Hourly" option

with st.sidebar:
    st.markdown("### Filter Options")

    start_date, end_date, frequency = date_range_slider(date(year=2020, month=1, day=1), date.today() + timedelta(days=365*2), frequency_options=list(FREQ_GROUPS.keys())[1:], key_prefix="gas_price")
    
start_dt = datetime.combine(start_date, datetime.min.time())
end_dt = datetime.combine(end_date, datetime.min.time())

display_metrics([current_gas_price_metric, total_gas_cost_metric, gas_storage_metric])

st.markdown(
    """
    Gas prices are a critical component of the energy market in Great Britain, influencing both electricity prices and the overall cost of energy for 
    consumers and businesses.
    This dashboard provides insights into the wholesale electricity and gas prices in Great Britain.
    You can explore the historical and forecasted prices, compare electricity and gas prices, and analyze the ratio of electricity to gas prices over time.
    Use the sidebar to filter the data by date range and frequency.
    """
)

display_chart(gas.create_price_chart(start_dt, end_dt, period_group=frequency))

st.markdown(
    """
    Gas storage levels are an important factor in the energy market, as they can influence gas prices and the availability of gas for electricity generation.
    This chart shows the historical gas storage levels in Great Britain, allowing you to analyze trends and patterns over time.
    """
)
display_chart(gas.create_storage_chart(start_dt, end_dt, period_group=frequency))
st.markdown("* Note: A day's storage is based on a rolling one month average of gas demand")
footer()