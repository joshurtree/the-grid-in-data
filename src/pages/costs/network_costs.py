import streamlit as st

overview_tab, tnuos_tab, duos_tab, bsuos_tab = st.tabs(["Overview", "TNUoS", "DUoS", "BSUoS"])

with overview_tab:
    st.header("Overview")
    st.write("This is the overview of the electricity prices.")

with tnuos_tab:
    st.header("TNUoS")
    st.write("This is the TNUoS section.")

with duos_tab:
    st.header("DUoS")
    st.write("This is the DUoS section.")

with bsuos_tab:
    st.header("BSUoS")
    st.write("This is the BSUoS section.")