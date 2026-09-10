from datetime import datetime, timedelta
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import backend.cfd as cfd 
from datasources.policy import cfd_dataset
from pages.base import display_chart

st.markdown('''
# Contract for Difference (CFD) 
Analysis of electricity price contracts and CFD payments.
''')

with st.sidebar:
    st.markdown("### Filter Options",)
    st.markdown("Select the date range and strike price to analyze the CFD payments.")
    start_date = st.date_input(
        "Start Date", value=(datetime.now() - timedelta(days=365)), key="cfd_start"
    )
    end_date = st.date_input("End Date", value=datetime.now(), key="cfd_end")
    technology = st.multiselect("Technology", options=cfd.get_available_technologies(), default=cfd.get_available_technologies())
    allocation_round = st.multiselect("Allocation Round", options=cfd.get_available_allocation_rounds(), default=cfd.get_available_allocation_rounds())

st.markdown("### CFD Payments")
st.markdown('''
    These charts show the costs involved in the Contract for Difference (CFD) scheme, which is designed to support low-carbon electricity generation in the UK. 
    The CFD scheme pays generators a guarenteed price by paying them the difference between the market price and a pre-agreed strike price for their electricity output.
    
    The first chart shows the total CFD payments made to generators over time, broken down by technology.
    The second chart shows the total CFD payments made to generators over time, broken down by strike price.
    ''')

cfd.filter_data(start_date, end_date, technology, allocation_round)
display_chart(cfd.create_cfd_chart())
display_chart(cfd.create_strike_price_chart())

st.markdown("### List of Generators")

search_term = st.text_input("Search for a generator (by name or technology):")
status = st.radio("Status",  ["All"] + list(cfd.get_available_statuses()), index=0, horizontal=True)

display_chart(
    cfd.show_generators(search_term, status), 
    column_config={
        "Expected Start Date": st.column_config.DateColumn(
            "Expected Start Date",
            format="DD MMM YYYY",
        ),
    },
)
