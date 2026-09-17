import streamlit as st

pages = {
    "" : [
        st.Page("pages/home.py", title="Home", icon=":material/house:"),
        st.Page("pages/links.py", title="Links", icon=":material/link:"),
    ],
    "Costs" : [
        st.Page("pages/costs/wholesale_prices.py", title="GB Energy Wholesale Prices", icon=":material/ev_station:"), 
        st.Page("pages/costs/cfds.py", title="Contracts for Difference", icon=":material/contract:"),
        st.Page("pages/costs/capacity_market.py", title="Capacity Market", icon=":material/brick:"),
        st.Page("pages/costs/balancing_costs.py", title="Balancing Costs", icon=":material/balance:"),
    ],
    "Security of supply" : [
        st.Page("pages/supply/capacity_factors.py", title="Capacity Factors", icon=":material/bolt:"),
        st.Page("pages/supply/gas.py", title="Gas Prices", icon=":material/mode_heat:"),
    ],
    # "Maps" : [
    #     st.Page("pages/live_map.py", title="GB Energy Generation Map", icon=":material/map:")
    # ]
}

# Add pages if the debug flag is set
if st.session_state.get("debug", True):
    pages["Debug"] = [
        st.Page("pages/debug/data_info.py", title="Data info", icon=":material/bug_report:")
    ]

if "__main__" == __name__:
    st.set_page_config(
        page_title="GB Energy Prices",
        page_icon=":material/bolt:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    pg = st.navigation(pages)
    pg.run()