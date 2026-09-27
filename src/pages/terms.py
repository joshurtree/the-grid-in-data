import streamlit as st
from pages.base import footer

st.title("Terms and Conditions")
st.markdown("""
            All the data and charts on this website are provided as is for informational purposes only. 
            While we strive to ensure the accuracy and reliability of the information presented, 
            we make no guarantees regarding its completeness or correctness. 

            Reproduction, distribution, or commercial use of the data and charts is permitted only with proper attribution to the source.
            The author(s) of this website are not responsible for any decisions made based on the information provided herein.

            The code for this website is open-source and available on [GitHub](https://github.com/joshurtree/our-grid-in-data). 
            It is provided under the [GPL-3.0 license](https://www.gnu.org/licenses/gpl-3.0.html), 
            which allows for free use, modification, and distribution of the code, 
            provided that any derivative works also comply with the same license.
            By using this website, you agree to these terms and conditions. 
""")
footer()