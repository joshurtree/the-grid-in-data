from datasources.datasource import DataSource, DataCategory, DataSet, self_provider
from datasources.providers import *
from backend.constants import RAW_DATA_PATH, MANUAL_DATA_PATH

cm_payments_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="capacity_market_payments",
    url="https://dp.lowcarboncontracts.uk/dataset/ea55663a-30b2-4b74-b72c-946de1622167/resource/1c4daa32-2358-43d4-b2d1-29e948c159cd/download/capacity_obligation_by_auction.csv",
)
cm_auctions_source = DataSource(providers=[ngeso_provider, neso_provider], category=DataCategory.POLICY, name="cm-auctions", url=f"{MANUAL_DATA_PATH}/cm-auctions.csv")
cm_awards_source = DataSource(providers=[neso_provider], category=DataCategory.POLICY, name="capacity_obligation_by_auction")

cm_forecast_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="capacity_market_forecast",
    url="https://dp.lowcarboncontracts.uk/dataset/a90f0e9b-d894-4d80-bedd-608a837d5e5d/resource/011a729d-5e58-4247-838e-601fd9bcf8d1/download/cm_forecast_cost.csv",
)

cfd_contracts_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="cfd_contracts",
    url="https://dp.lowcarboncontracts.uk/dataset/754ae1ec-3539-4bdf-86f5-ba204a56be76/resource/7bdfb0cb-fe99-44eb-b07b-2047e82f5601/download/cfd_contract_portfolio_status.csv",
)
cfd_settlements_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="cfd_settlements",
    url="https://dp.lowcarboncontracts.uk/dataset/8e8ca0d5-c774-4dc8-a079-347f1c180c0f/resource/5279a55d-4996-4b1e-ba07-f411d8fd31f0/download/actual_cfd_generation_and_avoided_ghg_emissions.csv",
    date_fields=["Settlement Date"]
)
cfd_locations_source = DataSource(
    providers=[lccc_provider],
    category=DataCategory.POLICY,
    name="cfd_locations",
    url="https://dp.lowcarboncontracts.uk/dataset/423d3c6b-d1ea-466d-a0f2-5d169003fe56/resource/f1416517-a6ff-4cd1-a364-22015a942a3f/download/cfd_locations_by_parliamentary_constituency.csv",
)
ro_source = DataSource(providers=[ofgem_provider], category=DataCategory.POLICY, name="renewables_obligation")
cfd_dataset = DataSet(datasources=[cfd_contracts_source, cfd_locations_source], name="cfd_data", category=DataCategory.POLICY)

