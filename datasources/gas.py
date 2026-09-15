from datasources.datasource import DataSource, DataCategory, DataSet
from datasources.providers import *
from backend.metric import NO_UNIT, Metric, CURRENCY, UNIT_PRICE

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

current_gas_price_metric = Metric(
    "Current Gas Price", 
    description="Current price of gas in pence per therm. Averaged over the last month", 
    unit=UNIT_PRICE)
total_gas_cost_metric = Metric(
    "Estimated Annual Gas Cost", 
    description="Estimated cost of gas in last year. Calculated by taking generation by gas power plants and assuming an efficiency of 40%", 
    unit=CURRENCY)
sparkgap_metric = Metric(
    "Spark Gap (Wholesale)", 
    description="Current difference between wholesale electricity prices and gas prices. Averaged over the last month", 
    unit=NO_UNIT)
