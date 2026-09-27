from figures.metric import CURRENCY, ENERGY, UNIT_PRICE, Metric, NO_UNIT
from .datasource import DataSource, DataCategory, DataSet
from .providers import *
from constants import DATE_FIELD, DATETIME_FIELD


system_electricity_price_source = DataSource(
    providers=[ons_provider],
    name="system_electricity_prices",
    category=DataCategory.SYSTEM,
    url="https://www.ons.gov.uk/economy/economicoutputandproductivity/output/datasets/systemaveragepricesofelectricity"
)
generation_source = DataSource(
    providers=[neso_provider],
    name="electricity_generation",
    category=DataCategory.SYSTEM,
    url="https://www.neso.energy/data-portal/historic-generation-mix/historic_gb_generation_mix",
    date_fields=[DATETIME_FIELD]
)
demand_source = DataSource(
    providers=[elexon_provider],
    name="electricity_demand",
    category=DataCategory.SYSTEM,
    url="https://bmrs.elexon.co.uk/demand-outurn"
)
embedded_generation_source = DataSource(
    providers=[neso_provider],
    name="embedded_generation",
    category=DataCategory.SYSTEM,
    url="https://www.neso.energy/data-portal/embedded-wind-and-solar-forecasts",
)
wholesale_price_source = DataSource(
    providers=[elexon_provider],
    name="wholesale_prices",
    category=DataCategory.SYSTEM,
    url="https://bmrs.elexon.co.uk/market-index-prices",
    date_fields=[DATETIME_FIELD]
)
generators_manual_source = DataSource(
    providers=[],
    name="generators",
    category=DataCategory.SYSTEM
)
repd_projects_source = DataSource(
    providers=[repd_provider],
    name="REPD",
    category=DataCategory.SYSTEM
)
bmus_source = DataSource(
    providers=[elexon_provider],
    name="bmus",
    category=DataCategory.SYSTEM
)
total_capacity_source = DataSource(
    providers=[dukes_provider],
    name="total_capacity",
    category=DataCategory.SYSTEM,
    url="https://www.gov.uk/government/statistics/electricity-chapter-5-digest-of-united-kingdom-energy-statistics-dukes"
)

bm_payments_source = DataSource(
    providers=[neso_provider],
    name="balancing_mechanism_payments",
    category=DataCategory.SYSTEM,
    url="https://www.neso.energy/data-portal/daily-balancing-costs-balancing-services-use-system",
    date_fields=[DATETIME_FIELD]
)

from .supply import daily_gas_prices_dataset

generators_dataset = DataSet(
    name="generators",
    datasources=[generators_manual_source, repd_projects_source, bmus_source],
    category=DataCategory.SYSTEM
)
half_hourly_dataset = DataSet(
    name="half_hourly_data",
    datasources=[wholesale_price_source, generation_source],
    category=DataCategory.SYSTEM,
    date_fields=[DATETIME_FIELD, "Settlement Date"]
)
daily_dataset = DataSet(
    name="daily_data",
    datasources=[wholesale_price_source, generation_source],
    category=DataCategory.SYSTEM,
    date_fields=[DATE_FIELD, "Settlement Date"]
)
gasvselec_dataset = DataSet(
    name="elec_vs_gas",
    datasources=[daily_dataset, daily_gas_prices_dataset],
    category=DataCategory.SYSTEM,
    date_fields=[DATE_FIELD]
)

current_wholesale_price_metric = Metric(
    "Current Wholesale Price", 
    description="Current price of wholesale electricity in £/MWh. Averaged over the last month", 
    unit=UNIT_PRICE)
sparkgap_metric = Metric(
    "Spark Gap (Wholesale)", 
    description="Current difference between wholesale electricity prices and gas prices. Averaged over the last month", 
    unit=NO_UNIT)

total_wholesale_cost_metric = Metric(
    "Annual Wholesale Cost", 
    description="Total cost of wholesale electricity in the last year", 
    unit=CURRENCY)
total_generation_metric = Metric(
    "Annual Electricity Generation", 
    description="Total electricity generation (including imports) in the last year", 
    unit=ENERGY)
annual_bm_payments_metric = Metric(
    "Annual Balancing Mechanism Payments", 
    description="Total payments made to the balancing mechanism in the last year", 
    unit=CURRENCY)