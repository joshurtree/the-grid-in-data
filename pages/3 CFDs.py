from datetime import datetime, timedelta
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from backend.cfd import CFDData, technologies, rounds
from backend.constants import TRANSFORMED_DATA_DIR

st.markdown('''
# Contract for Difference (CFD) Analysis Analyze electricity price contracts and CFD payments")
Analyze electricity price contracts and CFD payments
''')

with st.sidebar:
    st.markdown("### Filter Options")
    st.markdown("Select the date range and strike price to analyze the CFD payments.")
    start_date = st.date_input(
        "Start Date", value=(datetime.now() - timedelta(days=365)), key="cfd_start"
    )
    end_date = st.date_input("End Date", value=datetime.now(), key="cfd_end")
    technology = st.multiselect("Technology", options=technologies, default=technologies)
    allocation_round = st.multiselect("Allocation Round", options=rounds, default=rounds)

cfd_data = CFDData(
    start_date=start_date,
    end_date=end_date,
    technology=technology,
    allocation_rounds=allocation_round,
)

tab_overview, tab_technology, tab_strike_price, tab_contracts = st.tabs(
    ["Overview", "CFD by Technology", "CFD by Strike Price", "List of Generators"],
    width="stretch"
)

with tab_overview:
    st.markdown("### CFD Payments")
    st.markdown('''
        These charts show the costs involved in the Contract for Difference (CFD) scheme, which is designed to support low-carbon electricity generation in the UK. 
        The CFD scheme pays generators a guarenteed price by paying them the difference between the market price and a pre-agreed strike price for their electricity output.
        
        The first chart shows the total CFD payments made to generators over time, broken down by technology.
        The second chart shows the total CFD payments made to generators over time, broken down by strike price.
        ''')
with tab_technology:
    st.plotly_chart(cfd_data.create_cfd_chart(), width='stretch')

with tab_strike_price:
    st.plotly_chart(cfd_data.create_strike_price_chart(), width='stretch')

with tab_contracts:
    st.markdown("### List of Generators")
    generators = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'cfd_data.csv'))
    search_term = st.text_input("Search for a generator (by name or technology):")
    status = st.radio("Status",  ["All"] + list(generators['Status'].unique()), index=0, horizontal=True)
    if search_term:
        generators = generators[
            generators.apply(
                lambda row: search_term.lower() in str(row['Generator Name']).lower() or
                            search_term.lower() in str(row['Technology']).lower(),
                axis=1
            )
        ]
    if status != "All":
        generators = generators[generators['Status'] == status]
    st.dataframe(generators, width='stretch', hide_index=True)