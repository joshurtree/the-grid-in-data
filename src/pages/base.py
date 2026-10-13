from datetime import date, datetime, timedelta
import os
from plotly import graph_objects as go
import pandas as pd
import streamlit as st
from typing import Callable

from datasources.datasource import DataSet
from figures.chartset import Chart
from figures.metric import Metric
from constants import DATE_WINDOWS, FREQ_GROUPS

class BasePage:
    """Base class for all pages in the Streamlit app."""
    def __init__(self, show_date_slider: bool = True):
        self.show_date_slider = show_date_slider
        
    def __enter__(self):
        """Called when the page is loaded."""
        with st.sidebar:
            self.filter_container = st.container()
            with self.filter_container:
                st.markdown("### Filter Options")
            
            self.show_tabs = st.toggle("Show Extended Information", value=False, help="Show tabs for data and sources alongside charts.")

        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Called when the page is unloaded."""
        # Rethrow any exceptions that occurred during the page's execution
        if exc_type is not None:
            raise exc_value
        
        self.footer()
        return self          

    def display_metrics(self, metrics: list[Metric]) -> None:
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

    def display_raw_chart(self, schart: Chart, **kwargs) -> None:
        """Displays a raw chart in the Streamlit app."""
        if schart.chart is not None:
            st.plotly_chart(schart.chart, width='stretch', **kwargs)
            st.markdown(schart.dataset_info(), text_alignment="right")

    def display_sources(self, dataset: DataSet) -> None:
        """Displays a list of sources in the sidebar."""
        st.markdown("### Sources")
        for source in dataset.get_sources():
            st.markdown(f"* [{source.name}]({source.url})")

    def display_chart(self, chart: Chart, **kwargs):
        """Displays a chart in the Streamlit app."""
        chart_tabs = {
            "Chart": lambda chart, **kwargs: self.display_raw_chart(chart, **kwargs),
            "Data Table": lambda chart, **kwargs: st.dataframe(chart.table, hide_index=True, lazy=True, **kwargs),
            "Source Data": lambda chart: self.display_sources(chart.dataset)
        }

        st.markdown(f"### {chart.title}")
        
        if self.show_tabs is False:
            if chart.chart is not None:
                chart_tabs["Chart"](chart, **kwargs)
            else:
                chart_tabs["Data Table"](chart, **kwargs)
        else:
            tab_names = list(chart_tabs.keys()) if chart.chart is not None else list(chart_tabs.keys())[1:]  # Exclude "Chart" tab if no chart is available
            tabs = st.tabs(tab_names)
            for tab, tab_name in zip(tabs, tab_names):
                with tab:
                    chart_tabs[tab_name](chart, **kwargs)
        st.markdown(chart.description)
        
        
    def date_range_slider(
            self,
            start_date: date,
            end_date: date, 
            min_date: date|None = None, 
            max_date: date|None = None, 
            frequency="daily", 
            frequency_options: list[str] = list(FREQ_GROUPS.keys()), 
            key_prefix: str = "date_range",
            hide_frequency: bool = False
    ) -> tuple[pd.Timestamp, pd.Timestamp, str]:
        """Displays a date range slider in the sidebar and returns the selected start and end dates."""
        if min_date is None:
            min_date = start_date
        if max_date is None:
            max_date = end_date
        if len(frequency_options) > 1:
            frequency = st.radio(
                "Select Frequency",
                options=frequency_options,
                index=frequency_options.index(frequency) if frequency in frequency_options else 0,
                key=f"{key_prefix}_frequency",
                horizontal=True
            ) if not hide_frequency else frequency
        date_range = st.slider(
            "Select Date Range",
            min_value=min_date,
            max_value=max_date,
            value=(start_date, end_date),
            format="DD MMM YY",
            step=FREQ_GROUPS.get(frequency, timedelta(days=1)),
            key=f"{key_prefix}_slider",
            on_change=lambda: st.session_state.update({f"{key_prefix}_pills": "Custom"}),
            persist_state='session'
        )
    
        def update_slider_from_pills():
            selected_window = st.session_state.get(f"{key_prefix}_pills")
            if selected_window == "All":
                st.session_state[f"{key_prefix}_slider"] = (min_date, max_date)
            elif selected_window in DATE_WINDOWS:
                window = DATE_WINDOWS[selected_window]
                st.session_state[f"{key_prefix}_slider"] = (datetime.today() - window[0], datetime.today())
                st.session_state[f"{key_prefix}_frequency"] = window[1]

        alt_date_range = st.pills(
            "Quick Date Range",
            options=list(DATE_WINDOWS.keys()),
            label_visibility="collapsed",
            key=f"{key_prefix}_pills",
            on_change=update_slider_from_pills
        )

        return pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]), frequency

        
    def footer(self) -> None:
        """Displays a footer with the author's name and email."""
        with st.bottom:
            st.markdown(
                '''
                ---
                Copyright © [Josh Andrews](mailto:joshurtree@gmail.com) 2026
                [![Repo](https://badgen.net/badge/icon/GitHub?icon=github&label)](https://github.com/joshurtree/the-grid-in-data)
                [![Buy Me a Coffee](https://badgen.net/badge/icon/Buy%20Me%20a%20Coffee?icon=buymeacoffee&label)](https://www.buymeacoffee.com/joshurtree)
                ''')
            
