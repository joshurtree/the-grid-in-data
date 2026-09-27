import pandas as pd
import streamlit as st
import plotly.express as px
from figures.capacity_factors import create_capacity_factor_chart, create_capacity_factor_chart_by_window, create_capacity_factor_percentiles_chart
from pages.base import display_chart, footer

st.title("Capacity Factor Analysis")

with st.sidebar:
    st.header("Filter Options")
    selected_window = st.selectbox("Select Time Window", ['Daily', 'Weekly', 'Monthly', 'Quarterly'], index=1)
st.markdown("""
Analysis of capacity factors by fuel type, showing how efficiently different generation 
technologies are utilized throughout the year.
""")

display_chart(create_capacity_factor_chart())
display_chart(create_capacity_factor_chart_by_window(selected_window))

st.markdown("""
            * Note: The capacity factor is calculated based on the available capacity and actual generation.
            Does not account for unused generation due to curtailment or other operational constraints. 
            """)
display_chart(create_capacity_factor_percentiles_chart(selected_window))
footer()