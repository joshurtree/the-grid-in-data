import pandas as pd
import requests
from urllib import parse

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
