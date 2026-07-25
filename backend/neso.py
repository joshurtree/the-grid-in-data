import pandas as pd
import requests
from urllib import parse

def fetch_neso_data(sql_query: str) -> pd.DataFrame:
    """
    Fetch data from the Neso API using a SQL query.
    """
    params = {'sql': sql_query}
    response = requests.get('https://api.neso.energy/api/3/action/datastore_search_sql', params = parse.urlencode(params))
    data = response.json()["result"]
    df = pd.DataFrame(data["records"])
    return df

def fetch_embedded_generation(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch embedded generation data from the Neso API for a given date range.
    """
    sql_query = f'''SELECT * FROM  "db6c038f-98af-4570-ab60-24d71ebd0ae5" WHERE "DATE_GMT" >= '{start_date}' AND "DATE_GMT" <= '{end_date}' ORDER BY "DATE_GMT" ASC'''
    return fetch_neso_data(sql_query)