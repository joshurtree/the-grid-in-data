from datasources.datasource import DataSource, DataCategory, DataSet
from datasources.providers import *

ons_system_gas_price_source = DataSource(
    name="ons_system_gas_price",
    category=DataCategory.GAS, 
    providers=[ons_provider],  
    url="https://www.ons.gov.uk/economy/economicoutputandproductivity/output/datasets/systemaveragepricesapofgas",
)
ngas_system_gas_price_source = DataSource(
    name="ngas_system_gas_price",
    category=DataCategory.GAS, 
    providers=[nationalgas_provider],  
    url="https://data.nationalgas.com/find-gas-data"
)
gas_price_forecast_source = DataSource(
    name="gas_price_forecast", 
    category=DataCategory.GAS,
    providers=[poundf_provider],
    url="https://poundf.co.uk/uk-natural-gas",
)
daily_gas_prices_dataset = DataSet(
    name="daily_gas_prices", 
    datasources=[ons_system_gas_price_source, ngas_system_gas_price_source], 
    category=DataCategory.GAS,
    date_fields=["Date"]
)
monthly_gas_prices_dataset = DataSet(
    name="monthly_gas_prices", 
    datasources=[ons_system_gas_price_source, gas_price_forecast_source], 
    category=DataCategory.GAS,
    date_fields=["Date"]
)
