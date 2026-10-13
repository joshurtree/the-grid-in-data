import streamlit as st
from figures.balancing import balancing_costs
from constants import FREQ_GROUPS
from pages.base import BasePage
from  datasources.system import annual_bm_payments_metric

with BasePage() as page:
    with page.filter_container:
        frequency = st.radio(
            "Time Period",
            options=list(FREQ_GROUPS.keys())[1:],  # Exclude "Hourly" option
            index=2,
            horizontal=True,
        )
    st.title("Balancing Costs")
    page.display_metrics([annual_bm_payments_metric])
    st.markdown("""
    This page shows the balancing costs incurred by the grid. The costs are broken down into different 
    categories, including energy imbalance, frequency control, positive and negative reserve, 
    constraints, and other costs. Costs are paid for through the BUSos charge.
    """)
    page.display_chart(balancing_costs(frequency=frequency))
