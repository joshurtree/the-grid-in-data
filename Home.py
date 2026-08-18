"""
GB Electricity Prices - Streamlit Web Interface

Main entrypoint. Uses `st.navigation`/`st.Page` for sidebar navigation between
pages, each of which is implemented as a `render()` function in `pages/*.py`
reusing the existing backend chart/data functions.
"""
import streamlit as st

# energy_map_page = st.Page(
#     render_energy_map, title="GB Energy Generation Map", icon=":material/map:", url="/energy-map"
# )
# gasvselectricity_page = st.Page(
#     render_gasvselectricity, title="Electricity vs Gas Prices", icon=":material/local_gas_station:", url="/gas-vs-electricity"
# )
# prices_page = st.Page(
#     render_prices, title="GB Energy Wholesale Prices", icon=":material/payments:", url="/prices"
# )
# cfd_page = st.Page(
#     render_cfd, title="Contracts for Difference", icon=":material/description:", url="/cfd"
# )
st.set_page_config(
     page_title="GB Electricity Prices",
     layout="wide",
     page_icon=":zap:",
)

st.write("# GB Electricity Price Dashboard")


st.markdown(
"""
## Welcome to the GB Electricity Price Dashboard
A bunch of charts and tables to visualize and analyze electricity prices in Great Britain. Currently a work in progress, but feel free to explore the pages and provide feedback!

## About this app
This app provides a dashboard for visualizing and analyzing GB electricity prices.
"""
)

with st.bottom:
    st.markdown(
        """
        ---
        Made by [Josh Andrews](joshurtree@yahoo.com)
        """
    )