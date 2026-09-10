from backend.constants import DATE_FIELD
from datasources.datasource import DataSet, DataCategory
from datasources.system import half_hourly_dataset
from datasources.gas import daily_gas_prices_dataset
from datasources.policy import cfd_settlements_source, cm_payments_source


summary_dataset = DataSet(
    name="summary_dataset",
    datasources=[half_hourly_dataset, daily_gas_prices_dataset, cfd_settlements_source, cm_payments_source],
    category=DataCategory.SYSTEM,
    date_fields=[DATE_FIELD]
)