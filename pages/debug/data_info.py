import inspect
import importlib
from typing import Any, Optional
import pandas as pd
import streamlit as st

from datasources.datasource import DataSet, DataSource
import datasources.gas as gas
import datasources.policy as policy
import datasources.system as system

# /home/josh/projects/electricity-prices/pages/debug/data_info.py

st.title("Debug: Data sources & datasets")
st.write("Introspect DataSource and DataSet objects from datasources.* modules.")


st.html("""
    <script>
        function previewDataFrame(name) {
            const streamlitEvent = new CustomEvent("streamlit:previewDataFrame", { detail: { name } });
            window.dispatchEvent(streamlitEvent);
        }
    </script>
""")

def data_info(member: Any) -> Optional[dict]:
    df = member.load_data() if member.exists() else pd.DataFrame()
    return {
        "Name": member.name,
        "Exists": member.exists(),
        "Path": member.path(),
        "Number of records": len(df),
    }

for module in [gas, policy, system]:
    st.header(f"Module: {module.__name__}")
    sources = pd.DataFrame([data_info(member) for name, member in inspect.getmembers(module) if isinstance(member, DataSource)])
    st.header(f"Data sources")
    st.table(sources)   

    st.header(f"Datasets")
    datasets = pd.DataFrame([data_info(member) for name, member in inspect.getmembers(module) if isinstance(member, DataSet)])
    st.table(datasets)