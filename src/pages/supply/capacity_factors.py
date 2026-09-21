import pandas as pd
import streamlit as st
import plotly.express as px
from figures.capacity_factors import create_capacity_factor_chart
from pages.base import display_chart, footer

st.title("Capacity Factor Analysis")

st.markdown("""
Analysis of capacity factors by fuel type, showing how efficiently different generation 
technologies are utilized throughout the year.
""")

display_chart(create_capacity_factor_chart())
footer()