import streamlit as st
import pandas as pd
from datetime import date, timedelta
from figures.supply_vs_demand import create_supply_vs_demand_chart
from pages.base import footer, display_chart, display_metrics, date_range_slider

st.title("Electricity Demand")
with st.sidebar:
    st.header("Filters")
    start_date, end_date, frequency = date_range_slider(
        start_date=date.today() - timedelta(days=365), 
        end_date=date.today(), 
        min_date=date(2001, 1, 1), 
        max_date=date.today()
    )
display_chart(create_supply_vs_demand_chart(start_date, end_date, frequency))