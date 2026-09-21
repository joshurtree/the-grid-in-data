import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from constants import MANUAL_DATA_PATH
from figures.cm import create_cm_payments, create_cm_auction_scatter, inflator_functions
from figures.metric import Metric
from pages.base import display_chart, display_metrics, footer
from  datasources.policy import total_cm_payments_metric, total_cm_capacity_metric


with st.sidebar:
    st.markdown("### Filter Options")

    inflator_type = st.selectbox(
        "Select Price Year", 
        options=list(inflator_functions.keys()), 
        help="""
            Select the price year to adjust the auction prices for inflation. 
            'Delivery Year' adjusts prices to the delivery year, 'Auction Year' adjusts prices to the auction year, 
            and 'Constant' adjusts prices to a constant year (2024).
        """
    )

display_metrics([total_cm_payments_metric, total_cm_capacity_metric])
st.markdown("""
The Capacity Market (CM) is a mechanism designed to ensure that the electricity supply meets demand, particularly during peak periods. 
It provides payments to electricity generators to ensure they are available to supply electricity when needed. 
This analysis explores the payments made under the Capacity Market and the auction prices for capacity agreements.
""")

    
display_chart(create_cm_payments())
display_chart(create_cm_auction_scatter(inflator_type=inflator_type))
footer()
