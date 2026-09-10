import pandas as pd
import streamlit as st
from datasources.system import generation_source, capacity_source
import plotly.express as px

st.set_page_config(page_title="Capacity Factor Analysis", layout="wide")

st.title("Capacity Factor Analysis")

st.markdown("""
Analysis of capacity factors by fuel type, showing how efficiently different generation 
technologies are utilized throughout the year.
""")

# Load data
@st.cache_data
def load_data():
    generation = load_generation_data()
    capacity = load_capacity_data()
    return generation, capacity

generation_df, capacity_df = load_data()

# Calculate capacity factors
def calculate_capacity_factor(generation_df, capacity_df):
    """
    Calculate capacity factor = actual generation / (capacity * hours)
    """
    # Aggregate generation by year and fuel type (MWh)
    gen_annual = generation_df.groupby([generation_df.index.year, 'fuel_type'])['generation_mwh'].sum().reset_index()
    gen_annual.columns = ['year', 'fuel_type', 'total_generation_mwh']
    
    # Merge with capacity data
    merged = pd.merge(gen_annual, capacity_df, on=['year', 'fuel_type'], how='inner')
    
    # Calculate hours in year
    merged['hours_in_year'] = merged['year'].apply(lambda y: 8784 if y % 4 == 0 else 8760)
    
    # Calculate capacity factor
    merged['capacity_factor'] = (
        merged['total_generation_mwh'] / 
        (merged['capacity_mw'] * merged['hours_in_year'])
    )
    
    return merged

cf_data = calculate_capacity_factor(generation_df, capacity_df)

# Display annual capacity factors
st.header("Annual Capacity Factors by Fuel Type")

fig_annual = px.line(
    cf_data,
    x='year',
    y='capacity_factor',
    color='fuel_type',
    title='Capacity Factor Trends',
    labels={'capacity_factor': 'Capacity Factor', 'year': 'Year'}
)
fig_annual.update_yaxis(tickformat='.0%')
st.plotly_chart(fig_annual, use_container_width=True)

# Calculate monthly/seasonal variations
st.header("Seasonal Variation in Capacity Factors")

def calculate_monthly_cf(generation_df, capacity_df):
    """Calculate capacity factor by month"""
    gen_monthly = generation_df.copy()
    gen_monthly['year'] = gen_monthly.index.year
    gen_monthly['month'] = gen_monthly.index.month
    
    gen_agg = gen_monthly.groupby(['year', 'month', 'fuel_type'])['generation_mwh'].sum().reset_index()
    
    # Merge with capacity
    merged = pd.merge(gen_agg, capacity_df, on=['year', 'fuel_type'], how='inner')
    
    # Days per month
    merged['days_in_month'] = merged.apply(
        lambda row: pd.Period(f"{int(row['year'])}-{int(row['month'])}").days_in_month, 
        axis=1
    )
    merged['hours_in_month'] = merged['days_in_month'] * 24
    
    merged['capacity_factor'] = (
        merged['generation_mwh'] / 
        (merged['capacity_mw'] * merged['hours_in_month'])
    )
    
    return merged

monthly_cf = calculate_monthly_cf(generation_df, capacity_df)

# Select fuel type for detailed view
fuel_types = sorted(monthly_cf['fuel_type'].unique())
selected_fuel = st.selectbox("Select fuel type for seasonal analysis:", fuel_types)

fuel_data = monthly_cf[monthly_cf['fuel_type'] == selected_fuel]

fig_seasonal = px.box(
    fuel_data,
    x='month',
    y='capacity_factor',
    title=f'Monthly Capacity Factor Distribution - {selected_fuel}',
    labels={'capacity_factor': 'Capacity Factor', 'month': 'Month'}
)
fig_seasonal.update_yaxis(tickformat='.0%')
st.plotly_chart(fig_seasonal)

# Summary statistics
st.header("Summary Statistics")

latest_year = cf_data['year'].max()
latest_data = cf_data[cf_data['year'] == latest_year].sort_values('capacity_factor', ascending=False)

st.subheader(f"Capacity Factors for {latest_year}")
st.dataframe(
    latest_data[['fuel_type', 'capacity_factor', 'total_generation_mwh', 'capacity_mw']]
    .style.format({
        'capacity_factor': '{:.1%}',
        'total_generation_mwh': '{:,.0f}',
        'capacity_mw': '{:,.0f}'
    }),
    hide_index=True
)