from anyio import sleep
import pandas as pd
import requests
from time import sleep
from urllib import parse

from tqdm import tqdm

BALANCING_MECHANISM_ID = "daily-balancing-costs-balancing-services-use-of-system"
DEMAND_ID = "8a4a771c-3929-4e56-93ad-cdf13219dea5"
GENERATION_ID = "f93d1835-75bc-43e5-84ad-12472b180a98"
EMBEDDED_FORECAST_ID = "db6c038f-98af-4570-ab60-24d71ebd0ae5"
DEMAND_FORECAST_ID = "f93d1835-75bc-43e5-84ad-12472b180a98"


def fetch_neso_data(resource_id: str, **kwargs) -> pd.DataFrame:
    """
    Fetch data from the Neso API using a datastore query.
    """
    params = {'resource_id': resource_id, **kwargs}
    response = requests.get('https://api.neso.energy/api/3/action/datastore_search', params=params)

    if response.status_code != 200:
        raise Exception(f"Error fetching data from Neso API: {response.status_code} - {response.text}")
    
    return pd.DataFrame(response.json()["result"]["records"])

def fetch_extended_neso_data(resource_id: str, offset=0, **kwargs) -> pd.DataFrame:
    """
    Fetch all data from the Neso API using a datastore query, handling pagination.
    """
    all_records = pd.DataFrame()
    limit = 100  # Neso API limit per request
    
    while True:
        records = fetch_neso_data(resource_id, limit=limit, offset=offset, **kwargs)
        all_records = pd.concat([all_records, records], ignore_index=True)
        if len(records) < limit:
            break  # No more records to fetch

        sleep(1)  # To avoid hitting the API too quickly

        offset += limit

    return pd.DataFrame(all_records)

def fetch_all_records(resource_id: str, **kwargs) -> pd.DataFrame:
    url = "https://api.neso.energy/api/3/action/datapackage_show?id=" + resource_id
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error fetching data from Neso API: {response.status_code} - {response.text}")
    progress_bar = tqdm(total=len(response.json()["result"]["resources"]), desc="Fetching Neso Data", unit="resource")

    all_records = pd.DataFrame()
    for resource in response.json()["result"]["resources"]:
        if resource["format"].lower() != "csv":
            continue
        all_records = pd.concat([all_records, pd.read_csv(resource["path"])], ignore_index=True)
        progress_bar.update(1)
    progress_bar.close()
    
    return all_records