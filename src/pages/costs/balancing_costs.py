import streamlit as st
from backend.balancing import balancing_costs
from backend.constants import FREQ_GROUPS
from pages.base import display_chart, display_metrics, footer
from  datasources.system import annual_bm_payments_metric

with st.sidebar:
    st.markdown("### Filter Options")
    st.markdown("Select the time period to analyze the balancing costs.")
    frequency = st.radio(
        "Time Period",
        options=list(FREQ_GROUPS.keys())[1:],  # Exclude "Hourly" option
        index=2,
        horizontal=True,
    )
st.title("Balancing Costs")
display_metrics([annual_bm_payments_metric])
st.markdown("""
This page shows the balancing costs incurred by the grid. The costs are broken down into different 
categories, including energy imbalance, frequency control, positive and negative reserve, 
constraints, and other costs. Costs are paid for through the BUSos charge.
""")
display_chart(balancing_costs(frequency=frequency))
footer()