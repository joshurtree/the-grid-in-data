import streamlit as st

renewable_obligation, feed_in_tariff = st.tabs(["Renewable Obligation", "Feed-in Tariff"])

with renewable_obligation:
    st.header("Renewable Obligation")
    st.write("Content for Renewable Obligation")

with feed_in_tariff:
    st.markdown('''
        ## Feed-in Tariff
        Feed-in Tariffs (FiTs) are payments to ordinary energy users for the renewable electricity they generate. 
        The scheme was designed to encourage the uptake of renewable and low-carbon electricity generation technologies.
        They were introduced in 2010 and ran until 2019, when they were closed to new applicants.
        Solar PV installations, with contracts of 20 years, are the most common type of FiT. They received 25 year contracts for the first two years of the scheme. 
        Hence the costs will continue to rise with inflation until 2032, when the first contracts expire.
        ''')