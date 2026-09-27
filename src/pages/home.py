"""
GB Electricity Prices - Streamlit Web Interface

Main entrypoint. Uses `st.navigation`/`st.Page` for sidebar navigation between
pages, each of which is implemented as a `render()` function in `pages/*.py`
reusing the existing backend chart/data functions.
"""
import datetime
import os
import streamlit as st
from pages.base import footer

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
title = "The Grid in Data"
st.set_page_config(
     page_title=title,
     layout="wide",
     page_icon=":zap:",
)

st.write(f"# {title}")


st.markdown(
f"""
## {title}
A bunch of charts and tables to visualize and analyze electricity in Great Britain. 
Currently a work in progress, but feel free to explore the pages and provide feedback!

## About this website
This website provides a dashboard for visualizing and analyzing GB electricity prices.
"""
)

## Generate a news feed section by fetching commit messages from the repository and displaying them in a list format.
st.markdown("### Site Updates")
news_file = lambda x: os.path.join("data/manual/news", x)
news_content = []
for news_item in sorted(os.listdir("data/manual/news"), key=lambda x: os.path.getmtime(news_file(x)), reverse=True):
    news_date = datetime.datetime.fromtimestamp(os.path.getmtime(news_file(news_item))).strftime("%d %b %Y")
    with open(news_file(news_item), "r") as f:
        news_content.append((news_date, f.read().strip()))
st.table(news_content, border=False, hide_index=True, hide_header=True)
footer()