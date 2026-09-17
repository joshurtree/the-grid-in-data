from datetime import date, timedelta
import os
from plotly import graph_objects as go
import pandas as pd
import streamlit as st
from typing import Callable

from backend.chartset import Chart
from backend.metric import Metric
from backend.constants import FREQ_GROUPS

def display_metrics(metrics: list[Metric]) -> None:
    """Displays a list of metrics in a horizontal layout."""
    delta_color = lambda c1, c5: "red" if c1 <= 0 and c5 <= 0 else "violet" if c1 < 0 and c5 > 0 else "green" if c1 > 0 and c5 > 0 else "orange"
    with st.container(horizontal=True):
        for metric in metrics:
            st.metric(label=metric.name, 
                      value=metric.value_with_unit(), 
                      delta=metric.change(), 
                      delta_color=delta_color(metric.annual_change, metric.change_from_5_years_ago),
                      delta_arrow="off", 
                      help=f"{metric.description}. Comparison is with one and five years ago")

def display_chart(chart: Chart, **kwargs):
    """Displays a chart from a ChartSet object."""
    if chart.is_table():
        st.dataframe(chart.chart, hide_index=True, width='stretch', height='content', **kwargs)
    else:
        st.plotly_chart(chart.figure(), **kwargs)
    st.markdown(chart.dataset_info(), text_alignment="right")

def date_range_slider(
        start_date: date, 
        end_date: date, 
        min_date: date|None = None, 
        max_date: date|None = None, 
        frequency="daily", 
        frequency_options: list[str] = list(FREQ_GROUPS.keys()), 
        key_prefix: str = "date_range"
) -> tuple[pd.Timestamp, pd.Timestamp, str]:
    """Displays a date range slider in the sidebar and returns the selected start and end dates."""
    if len(frequency_options) > 1:
        frequency = st.radio(
            "Select Frequency",
            options=frequency_options,
            index=frequency_options.index(frequency) if frequency in frequency_options else 0,
            key=f"{key_prefix}_frequency",
            horizontal=True
        )
    date_range = st.slider(
        "Select Date Range",
        min_value=min_date or start_date,
        max_value=max_date or end_date,
        value=(start_date, end_date),
        format="DD MMM YY",
        step=FREQ_GROUPS.get(frequency, timedelta(days=1)),
        key=f"{key_prefix}_slider"
    )
    return pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]), frequency

def footer():
    """Displays a footer with the author's name and email."""
    with st.container():
        st.markdown(
            """
            ---
            Copyright © [Josh Andrews](mailto:joshurtree@gmail.com) 2026
            """
        )