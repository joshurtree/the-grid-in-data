from backend.chartset import Chart
from plotly import graph_objects as go
import pandas as pd
import streamlit as st
from typing import Callable

def display_chart(chart: Chart, **kwargs):
    """Displays a chart from a ChartSet object."""
    if chart.is_table():
        st.dataframe(chart.chart, hide_index=True, width='stretch', height='content', **kwargs)
    else:
        st.plotly_chart(chart.chart, **kwargs)
    st.markdown(chart.dataset_info(), text_alignment="right")

# Add a panel to the top right of the page showing metrics about the total cost
def display_metrics(metrics: dict):
    """Displays a set of metrics in a panel."""
    with st.container():
        cols = st.columns(len(metrics))
        for col, (label, value) in zip(cols, metrics.items()):
            st.metric(label, value)