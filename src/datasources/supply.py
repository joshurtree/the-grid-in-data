from .datasource import DataSource, DataCategory, DataSet
from .providers import *
from figures.metric import DAYS, NO_UNIT, Metric, CURRENCY, UNIT_PRICE

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
gas_storage_source = DataSource(
    name="gas_storage", 
    category=DataCategory.GAS,
    providers=[nationalgas_provider],
    url="https://data.nationalgas.com/find-gas-data"
)

daily_gas_prices_dataset = DataSet(
    name="daily_gas_prices", 
    datasources=[ons_system_gas_price_source, ngas_system_gas_price_source], 
    category=DataCategory.GAS,
    date_fields=["Date"]
)
monthly_gas_prices_dataset = DataSet(
    name="monthly_gas_prices", 
    datasources=[daily_gas_prices_dataset, gas_price_forecast_source], 
    category=DataCategory.GAS,
    date_fields=["Date"]
)
gas_demand_source = DataSource(
    name="gas_demand", 
    category=DataCategory.GAS,
    providers=[nationalgas_provider],
    url="https://data.nationalgas.com/find-gas-data"
)
gas_storage_capacity_source = DataSource(
    name="gas_storage_capacity", 
    category=DataCategory.GAS,
    providers=[dukes_provider],
    url="https://www.gov.uk/government/statistics/natural-gas-chapter-4-digest-of-united-kingdom-energy-statistics-dukes"
)

gas_storage_dataset = DataSet(
    name="gas_storage", 
    datasources=[gas_storage_source, gas_storage_capacity_source,gas_demand_source], 
    category=DataCategory.GAS,
    date_fields=["Date"]
)
current_gas_price_metric = Metric(
    "Current Gas Price", 
    description="Current price of gas in £/MWh. Averaged over the last month", 
    unit=UNIT_PRICE)
total_gas_cost_metric = Metric(
    "Estimated Annual Gas Cost", 
    description="Estimated cost of gas in last year. Calculated by taking generation by gas power plants and assuming an efficiency of 40%", 
    unit=CURRENCY)
gas_storage_metric = Metric(
    "Gas Storage", 
    description="Current gas storage in the UK in GWh", 
    unit=DAYS
)

from .system import daily_dataset

capacity_factors_source = DataSource(
    providers=[energy_trends_provider],
    name="capacity_factors",
    category=DataCategory.SYSTEM,
    url="data/manual/capacity_factors.csv"
)

capacity_factors_dataset = DataSet(
    name="capacity_factors",
    datasources=[capacity_factors_source, daily_dataset],
    category=DataCategory.SYSTEM,
    date_fields=["Date"]
)
