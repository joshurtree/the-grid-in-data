from datetime import datetime, timedelta, date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from backend.constants import NESO_GENERATION_TYPES
import backend.gbwep as gbwep
from pages.base import date_range_slider, display_chart, display_metrics, footer
from datasources.system import current_wholesale_price_metric, total_wholesale_cost_metric, total_generation_metric

with st.sidebar:
    st.markdown("### Filter Options")
    st.markdown(
        "Select the date range, target generation type, and minimum usage "
        "percentage to filter the data."
    )
    st.markdown(
        "The chart shows the electricity prices over time, while the table "
        "provides detailed statistics for the selected generation type."
    )
    start_date, end_date, frequency = date_range_slider(
        start_date=(datetime.now() - timedelta(days=365)).date(),
        end_date=datetime.now().date(),
        min_date=datetime(2017, 1, 1).date(),
        max_date=datetime.now().date(),
        frequency="daily",
        key_prefix="wholesale_prices_date"
    )
    target_keys = list(NESO_GENERATION_TYPES.values())
    default_index = target_keys.index("Low Carbon") if "Low Carbon" in target_keys else 0
    target = st.selectbox(
        "Target Generation",
        options=target_keys,
        index=default_index,
    )
    usage = st.slider("Usage (%)", min_value=0, max_value=100, value=[0, 100], step=1)


st.markdown("## GB Wholesale Electricity Prices")
display_metrics([current_wholesale_price_metric, total_wholesale_cost_metric, total_generation_metric])
st.markdown(
    "This chart shows the relationship between wholesale electricity prices and generation types over time. "
    "The color of the points represents the percentage of the selected generation type in the total generation mix."
)

display_chart(gbwep.create_chart(start_date, end_date, frequency, target, usage))
display_chart(gbwep.create_table(start_date, end_date, target, usage))
footer()

