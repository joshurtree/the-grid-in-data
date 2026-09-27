"""Client for the National Gas (formerly National Grid Gas Transmission)
public data API, published via the API developer portal at
https://apideveloper.nationalgas.com/s/

The portal itself is a JS-rendered Salesforce Experience Cloud site so its
endpoint reference isn't scrapeable, but the underlying data API (which
backs https://data.nationalgas.com) is a simple, unauthenticated REST
endpoint that returns CSV downloads. This is confirmed working (see
`fetch-data.py`'s National Gas price fetch) using:

    GET https://data.nationalgas.com/api/find-gas-data-download
        ?ids=<data item id>            e.g. PUBOB603, PUBOBJ2350
        &applicableFor=Y
        &dateFrom=YYYY-MM-DD
        &dateTo=YYYY-MM-DD
        &dateType=GASDAY
        &latestFlag=Y|N
        &type=CSV

which returns a CSV with columns: `Applicable At`, `Applicable For`,
`Data Item`, `Generated Time`, `Quality Indicator`, `Value`.

Data item IDs (e.g. `PUBOB603` for National Balancing Point gas price,
`PUBOBJ2350` for a storage-related item) can be found by browsing the data
item catalog at https://data.nationalgas.com/find-gas-data or your
registered application's catalog on the developer portal.

Typical usage:

    from backend.nationalgas import NationalGasClient

    client = NationalGasClient()
    df = client.fetch_data_item("PUBOB603", date(2026, 1, 1), date(2026, 1, 31))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from io import BytesIO
import os

import pandas as pd
import requests

from constants import DATE_FIELD
from datasources.datasource import DataSource

# Point OpenSSL at certifi's CA bundle. Some Python builds (e.g. the portable
# CPython downloaded by `uv`) don't have a system CA bundle wired up, which
# causes `ssl.SSLCertVerificationError: unable to get local issuer
# certificate` when fetching data over HTTPS.
os.environ.setdefault("SSL_CERT_FILE", __import__("certifi").where())

NATIONAL_GAS_API = "https://data.nationalgas.com/api/find-gas-data-download"

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# A few commonly used data item IDs. Extend this as you discover more via
# https://data.nationalgas.com/find-gas-data
@dataclass
class NationalGasDataItem:
    """Represents a National Gas data item ID and its description."""
    id: str
    name: str
    multiplier: float = 1.0  # Optional multiplier to apply to the raw value (default: 1.0)


STORAGE = NationalGasDataItem(id="PUBOBJ2350", name="Gas Reserves (GWh)")
NBP_GAS_PRICE = NationalGasDataItem(id="PUBOB603", name="Price", multiplier=10.0)
DEMAND = NationalGasDataItem(id="PUBOBJ1030", name="Gas Demand (GWh)", multiplier=1/1000000.0)


class NationalGasAPIError(RuntimeError):
    """Raised when the National Gas API returns an unexpected response."""


@dataclass
class NationalGasClient:
    """Thin wrapper around the National Gas public "find gas data" REST API."""

    base_url: str = NATIONAL_GAS_API
    headers: dict = field(default_factory=lambda: dict(DEFAULT_HEADERS))
    session: requests.Session = field(default_factory=requests.Session)

    def update_data_item(self, data_item: NationalGasDataItem, df: pd.DataFrame) -> pd.DataFrame:
        """Update a DataFrame with the latest values for a National Gas data item.

        Args:
            data_item: The National Gas data item to fetch.
            df: The existing DataFrame to update.

        Returns:
            A new DataFrame with the updated values for the specified data item.
        """

        start_date = df[DATE_FIELD].max() + timedelta(days=1) if DATE_FIELD in df.columns else date.today() - timedelta(days=5*366)  # Default to 5 years ago if no start date is provided
        if start_date is not None and start_date >= datetime.today():
            print(f"No new data to fetch for {data_item.name!r}; latest date in DataFrame is {start_date}.")
            return df
        
        new_data = self.fetch_data_item(data_item, date_from=start_date)
        df = pd.concat([df, new_data], ignore_index=True).drop_duplicates(subset=[DATE_FIELD])
        return df
    
    def fetch_data_item(
        self,
        data_item: NationalGasDataItem,
        date_from: date | datetime | str | None = None,
        date_to: date | datetime | str | None = None,
        date_type: str = "GASDAY",
        latest_only: bool = True,
        applicable_for: str = "Y",
    ) -> pd.DataFrame:
        """Fetch a data item's values over a date range as a DataFrame.

        Args:
            data_item_id: The National Gas data item ID (e.g. `PUBOB603`).
            date_from: Start of the date range (defaults to 30 days ago).
            date_to: End of the date range (defaults to today).
            date_type: The date type to filter on, e.g. `GASDAY`.
            latest_only: If True, only the latest published revision for
                each date is returned (`latestFlag=Y`); set False to
                retrieve every revision (`latestFlag=N`).
            applicable_for: Passed through as the `applicableFor` query
                parameter (`Y` by default, matching the confirmed working
                request pattern).

        Returns:
            A DataFrame with columns `Applicable At`, `Applicable For`,
            `Data Item`, `Generated Time`, `Quality Indicator`, `Value`.
        """
        if date_to is None:
            date_to = date.today()
        if date_from is None:
            date_from = date.today() - timedelta(days=5*366)  # Default to 5 years ago if no start date is provided

        def _fmt(d):
            if isinstance(d, (date, datetime)):
                return d.strftime("%Y-%m-%d")
            return d
        print(f"Fetching data item {data_item.name!r} from National Gas API for date range {_fmt(date_from)} to {_fmt(date_to)}...")
        params = {
            "applicableFor": applicable_for,
            "dateFrom": _fmt(date_from),
            "dateTo": _fmt(date_to),
            "dateType": date_type,
            "latestFlag": "Y" if latest_only else "N",
            "ids": data_item.id,
            "type": "CSV",
        }

        response = self.session.get(self.base_url, params=params, headers=self.headers, timeout=30)
        if response.status_code != 200:
            raise NationalGasAPIError(
                f"Error fetching data item {data_item.name!r} from National Gas API: "
                f"{response.status_code} - {response.text[:500]}"
            )
        
        if not response.content or response.content.strip() == b'':
            print(f"Warning: Received empty response for data item {data_item.name!r} from National Gas API.")
            return pd.DataFrame(columns=[DATE_FIELD, data_item.name])

        try:
            df = pd.read_csv(BytesIO(response.content))
            df.rename(columns={'Applicable For': DATE_FIELD, 'Value': data_item.name}, inplace=True)
            df[DATE_FIELD] = pd.to_datetime(df[DATE_FIELD], format='%d/%m/%Y', errors='coerce')
            df.drop(columns=['Applicable At', 'Data Item', 'Generated Time', 'Quality Indicator'], inplace=True)
            if data_item.multiplier != 1.0:
                df[data_item.name] = df[data_item.name] * data_item.multiplier
            return df
        except Exception as exc:
            raise NationalGasAPIError(
                f"Failed to parse CSV response for data item {data_item.name!r}: {exc}\n"
                f"Response body (truncated): {response.text[:500]}"
            ) from exc

# Backwards-compatible functional wrapper, matching the original signature
# used elsewhere in this codebase.
def fetch_national_gas_data(data_item: NationalGasDataItem, params: dict | None = None) -> pd.DataFrame:
    """Fetch gas data from the National Gas API for a single data item ID.

    Kept for backwards compatibility; prefer `NationalGasClient.fetch_data_item`
    for new code, since it provides sensible defaults and clearer errors.
    """
    params = dict(params or {})
    client = NationalGasClient()
    return client.fetch_data_item(
        data_item,
        date_from=params.get("dateFrom"),
        date_to=params.get("dateTo"),
        date_type=params.get("dateType", "GASDAY"),
        latest_only=params.get("latestFlag", "Y") != "N",
        applicable_for=params.get("applicableFor", "Y"),
    )


def update_national_gas_datasource(datasource: DataSource, data_item: NationalGasDataItem) -> None:
    """Update a DataSource with the latest values for a National Gas data item.

    Args:
        datasource: The DataSource to update.
        data_item: The National Gas data item to fetch.
    """
    client = NationalGasClient()
    existing_df = datasource.load_data() if datasource.exists() else pd.DataFrame()
    updated_df = client.update_data_item(data_item, existing_df)
    datasource.save_data(updated_df)