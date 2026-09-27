from figures.metric import CURRENCY, POWER, Metric
from .datasource import DataSource, DataCategory, DataSet
from .providers import *
from .system import generation_source
from constants import RAW_DATA_PATH, MANUAL_DATA_PATH


cm_payments_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="capacity_market_payments",
    url="https://dp.lowcarboncontracts.uk/dataset/capacity-obligation-by-auction",
)
cm_auctions_source = DataSource(
    providers=[ngeso_provider, neso_provider], 
    category=DataCategory.POLICY, 
    name="cm-auctions", 
    url=f"{MANUAL_DATA_PATH}/cm-auctions.csv"
)
cm_awards_source = DataSource(
    providers=[ngeso_provider, neso_provider], 
    category=DataCategory.POLICY, 
    name="capacity_market_awards",
)

cm_forecast_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="capacity_market_forecast",
    url="https://dp.lowcarboncontracts.uk/dataset/cm-forecast-cost",
)

cfd_contracts_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="cfd_contracts",
    url="https://dp.lowcarboncontracts.uk/dataset/cfd-contract-portfolio-status",
)
cfd_settlements_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="cfd_settlements",
    url="https://dp.lowcarboncontracts.uk/dataset/actual-cfd-generation-and-avoided-ghg-emissions",
    date_fields=["Settlement Date"]
)
cfd_locations_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="cfd_locations",
    url="https://dp.lowcarboncontracts.uk/dataset/cfd-locations-by-parliamentary-constituency",
)

cm_extended_forecast_dataset = DataSet(datasources=[cm_forecast_source], name="cm_extended_forecast", category=DataCategory.POLICY)

ro_source = DataSource(providers=[ofgem_provider], category=DataCategory.POLICY, name="renewables_obligation")
ets_source = DataSource(providers=[ofgem_provider], category=DataCategory.POLICY, name="emissions_trading_scheme", url="https://www.gov.uk/government/publications/taking-part-in-the-uk-emissions-trading-scheme-markets/cost-containment-mechanism-ccm-trigger-prices-and-average-monthly-prices-full-table")

cfd_dataset = DataSet(datasources=[cfd_contracts_source, cfd_locations_source], name="cfd_data", category=DataCategory.POLICY)
carbon_taxes_dataset = DataSet(datasources=[ets_source, generation_source], name="carbon_taxes", category=DataCategory.POLICY)

total_cfd_payments_metric = Metric("Annual CFD Payments", description="Annual payments for Contracts for Difference (CFD) projects", unit=CURRENCY)
total_cfd_capacity_metric = Metric("Total CFD Capacity", description="Total capacity obtained through Contracts for Difference (CFD)", unit=POWER)
total_cm_payments_metric = Metric("Annual Capacity Market Payments", description="Annual payments to Capacity Market providers", unit=CURRENCY)
total_cm_capacity_metric = Metric("Capacity Obtained", description="Capacity obtained for current delivery year through the Capacity Market", unit=POWER)