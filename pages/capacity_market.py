import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from backend.constants import MANUAL_DATA_PATH
from backend.cm import create_cm_payments, create_cm_auction_scatter, inflator_functions
from pages.base import display_chart

st.markdown("## GB Capacity Market Analysis")

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

st.markdown("""
The Capacity Market (CM) is a mechanism designed to ensure that the electricity supply meets demand, particularly during peak periods. 
It provides payments to electricity generators to ensure they are available to supply electricity when needed. 
This analysis explores the payments made under the Capacity Market and the auction prices for capacity agreements.

The main driver of the prices in the Capacity Market is the balance between available capacity and the expected demand. 
Capacity is awarded through a descending clock auction process. 
When there is a shortage of capacity it ends in an earlier round with a higher price. Such as the 2024/25 T-4 auction where available capacity exceeded demand by only a
gigawatt (GW), leading to it ending in round 3 with a price of £65/kW/year. A year later the 2025/36 T-4 auction, available capacity was 4 GW greater than demand,
resulting in it ending in round 10 with a price of £27.0/kW/year.""")

    
display_chart(create_cm_payments())
display_chart(create_cm_auction_scatter(inflator_type=inflator_type))