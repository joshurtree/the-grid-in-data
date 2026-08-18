import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import backend.elecvsgas as elecvsgas
from backend.constants import PERIOD_GROUPS


def _fig_from_error(msg):
    fig = go.Figure()
    fig.update_layout(title=msg)
    return fig


def _safe_chart(func, start_date, end_date, frequency):
    result = func(start_date, end_date, frequency)
    if isinstance(result, str):
        return _fig_from_error(f"Error: {result}")
    return result


st.markdown("## Gas Prices")

frequencies = list(PERIOD_GROUPS.keys())[1:]  # Exclude "Hourly" option

with st.sidebar:
    st.markdown("### Filter Options")
    start_date = st.date_input(
        "Start Date", value=datetime(year=2020, month=1, day=1).date(), key="evg_start"
    )
    end_date = st.date_input(
        "End Date",
        value=(datetime.now() + timedelta(days=730)).date(),
        key="evg_end",
    )
    frequency = st.radio("Frequency", options=frequencies, key="evg_frequency", horizontal=True)

start_dt = datetime.combine(start_date, datetime.min.time())
end_dt = datetime.combine(end_date, datetime.min.time())

tab_overview, tab_gas, tab_comparison, tab_ratio = st.tabs(
    ["Overview", "Gas prices (Past and Future)", "Price Comparison with Electricity", "Spark gap (wholesale)"],
    width="stretch"
)

with tab_overview:
    st.markdown(
        """
        Gas prices are a critical component of the energy market in Great Britain, influencing both electricity prices and the overall cost of energy for 
        consumers and businesses.
        This dashboard provides insights into the wholesale electricity and gas prices in Great Britain.
        You can explore the historical and forecasted prices, compare electricity and gas prices, and analyze the ratio of electricity to gas prices over time.
        Use the sidebar to filter the data by date range and frequency.
        """
    )
with tab_gas:
    st.markdown(
        """
        This page shows the wholesale gas prices over a specified date range and frequency.
        You can select the start and end dates, as well as the frequency of the data (daily, weekly, or monthly).
        The chart will update automatically based on your selections.
        """
    )
    price_fig = _safe_chart(elecvsgas.create_price_chart, start_dt, end_dt, frequency)
    st.plotly_chart(price_fig, width='stretch')
    st.markdown(
        """
        The gas prices are displayed in pence per kilowatt-hour (p/kWh). The price data for the first day of each month is used for the monthly frequency.
        Past data is sourced from the [ONS](https://www.ons.gov.uk/) and future data is from [Pound Forcast](https://poundf.co.uk/uk-natural-gas).
        Additional verification of forecast using GB Natural Gas Futures data from [ICE](https://www.theice.com/products/279/UK-Natural-Gas-Futures/data?marketId=566&span=1).
        """
    )

with tab_comparison:
    st.markdown(
        """
        This page allows you to compare the wholesale electricity and gas prices over a specified date range and frequency.
        You can select the start and end dates, as well as the frequency of the data (daily, weekly, or monthly).
        The chart will update automatically based on your selections.
        """
    )
    evg_fig = _safe_chart(elecvsgas.create_chart, start_dt, end_dt, frequency)
    st.plotly_chart(evg_fig, width='stretch')

with tab_ratio:
    st.markdown(
        """
        This tab shows the ratio of electricity price to gas price over time. 
        It provides insights into how the two energy sources compare in terms of cost.
        """
    )
    ratio_fig = _safe_chart(elecvsgas.ratio_chart, start_dt, end_dt, frequency)
    st.plotly_chart(ratio_fig, width='stretch')

