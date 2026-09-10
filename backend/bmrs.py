import requests
import pandas as pd
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from tqdm import tqdm
from backend.constants import ELEXON_GENERATION_TYPES

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/"
FUEL_TYPES = [
  "BIOMASS",
  "CCGT",
  "COAL",
  "INTELE",
  "INTELEC",
  "INTEW",
  "INTFR",
  "INTGRNL",
  "INTIFA2",
  "INTIRL",
  "INTNED",
  "INTNEM",
  "INTNSL",
  "INTVKL",
  "NPSHYD",
  "NUCLEAR",
  "OCGT",
  "OIL",
  "OTHER",
  "PS",
  "WIND"
]

def fetch_bmrs_data(endpoint, params=None, is_list=False) -> pd.DataFrame:
    """
    Fetch data from the BMRS API.

    Args:
        endpoint (str): The specific endpoint to fetch data from.
        params (dict, optional): Query parameters for the request.

    Returns:
        pd.DataFrame: DataFrame containing the fetched data.
    """
    url = BASE_URL + endpoint
    response = requests.get(url, params=params)
    response.raise_for_status()  # Raise an error for bad responses
    
    # Convert JSON data to DataFrame
    return pd.DataFrame(response.json()['data']) if not is_list else pd.DataFrame(response.json())

def fetch_extended_bmrs_data(endpoint_func, start_date: date, description: str) -> pd.DataFrame:
    """
    Fetch extended data from the BMRS API, handling pagination.

    Args:
        endpoint_func (str): The specific endpoint function to fetch data from.
        params (dict, optional): Query parameters for the request.

    Returns:
        pd.DataFrame: DataFrame containing the fetched data.
    """
    df = pd.DataFrame()
    date_ranges = pd.date_range(start=start_date, end=date.today(), freq='7D')
    progress_bar = tqdm(total=len(date_ranges), desc=description, unit='request')
    for start in date_ranges:
        end = start + timedelta(days=7)
        response = endpoint_func(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

        df = pd.concat([df, response], ignore_index=True)
        progress_bar.update(1)
    progress_bar.close()
    return df

def time_to_settlement_period(dt: datetime) -> int:
    """
    Convert a datetime object to the corresponding settlement period.

    Args:
        dt (datetime): The datetime object to convert.

    Returns:
        int: The settlement period (1-48).
    """
    # Settlement periods are 30 minutes each, starting from 00:00
    return (dt.hour * 2) + (1 if dt.minute >= 30 else 0) + 1

def get_generators() -> pd.DataFrame:
    """
    Fetch generator data from the BMRS API.

    Returns:
        pd.DataFrame: DataFrame containing generator data.
    """
    return fetch_bmrs_data("reference/bmunits/all", is_list=True)

def fetch_FPN(date: datetime, bmus: list[str] = None) -> pd.DataFrame:
    """
    Fetch Final Physical Notification (FPN) data from the BMRS API.

    Returns:
        pd.DataFrame: DataFrame containing FPN data.
    """
    params = {
        "dataset": "PN",
        "settlementDate": date.strftime('%Y-%m-%d'),
        "settlementPeriod": time_to_settlement_period(date)
    }
    #print(f"Fetching FPN data for {date.strftime('%Y-%m-%d %H:%M')} and settlement period {time_to_settlement_period(date)}")
    
    if bmus is not None:
        params["bmUnit[]"] = bmus
    return fetch_bmrs_data("balancing/physical/all",  params=params)

def fetch_generation(dateFrom: datetime, dateTo: datetime, bmus: list[str] = None) -> pd.DataFrame:
    """
    Fetch generation data from the BMRS API.

    Args:
        dateFrom (datetime): Start date for fetching generation data.
        dateTo (datetime): End date for fetching generation data.
        bmus (list[str], optional): List of BM Unit identifiers to filter by.

    Returns:
        pd.DataFrame: DataFrame containing generation data.
    """
    params = {
        "settlementDateFrom": dateFrom.strftime('%Y-%m-%d'),
        "settlementDateTo": dateTo.strftime('%Y-%m-%d'),
    }

    return fetch_bmrs_data("generation/outturn/summary", params=params)

def fetch_generation_by_type(dateFrom: datetime = datetime.now() - timedelta(days=1), dateTo: datetime = datetime.now()) -> pd.DataFrame:
    """
    Fetch generation data by type from the BMRS API.

    Args:
        dateFrom (datetime): Start date for fetching generation data.
        dateTo (datetime): End date for fetching generation data.

    Returns:
        pd.DataFrame: DataFrame containing generation data by type.
    """
    params = {
        "startTime": dateFrom.strftime('%Y-%m-%d'),
        "endTime": dateTo.strftime('%Y-%m-%d'),
    }

    data = fetch_bmrs_data("generation/outturn/summary", params, True)
    
    if data.empty:
        return pd.DataFrame(columns=['startTime'] + list(ELEXON_GENERATION_TYPES.keys()))
    # Convert `data: { "fuelType": ..., "generation": ... }` to `fuelType`: `generation`
    for fuel_type in ELEXON_GENERATION_TYPES.keys():
        column = fuel_type if not fuel_type.startswith("INT") else "IMPORTS"
        data[column] = data['data'].apply(lambda x: next((item['generation'] for item in x if item['fuelType'] == fuel_type), 0))
    data.drop(columns=['data'], inplace=True)
    return data

def get_bid_accepts(unit: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch bid accept data from the BMRS API.

    Args:
        unit (str): The unit identifier for which to fetch bid accept data.
        start_date (str): Start date in 'YYYY-MM-DD'
        end_date (str): End date in 'YYYY-MM-DD'

    Returns:
        pd.DataFrame: DataFrame containing bid accept data.
    """
    params = {
        "bmUnit": unit,
        "from": datetime.strftime(start_date, '%Y-%m-%dT00:00Z'),
        "to": datetime.strftime(end_date, '%Y-%m-%dT23:59Z')
    }

    return fetch_bmrs_data("balancing/acceptances", params=params)

def constraint_payments_analysis():
    """
    Analyze constraint payments for solar generators between June 1, 2025, and June 14, 2026.
    """
    generators = get_generators()
    generators = generators[generators['bmUnitName'].str.contains("solar", case=False, na=False)]
    print(generators)

    constraints = 0
    total_increased = 0
    total_decreased = 0
    total_accepted = 0

    for unit in generators.itertuples(index=False):
        print(f"Generation capacity for unit {unit.bmUnitName}: {unit.generationCapacity} MW")
        start_date = datetime(2025, 6, 1)
        end_date = datetime(2026, 6, 14)

        # Break down into weekly intervals
        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + pd.Timedelta(weeks=1) - pd.Timedelta(days=1), end_date)
            #print(f"Fetching bid acceptances for unit {unit.bmUnitName} from {current_start.date()} to {current_end.date()}")
            try:
                acceptances = get_bid_accepts(unit.elexonBmUnit, current_start, current_end)
                if len(acceptances) > 0:
                    for acceptance in acceptances.itertuples(index=False):
                        period = pd.to_datetime(acceptance.timeTo) - pd.to_datetime(acceptance.timeFrom)
                        mwhAccepted = acceptance.levelFrom - acceptance.levelTo * period.total_seconds() / 3600  # Convert to MWh

                        if mwhAccepted == 0:
                            continue  # Skip if no energy was accepted
                        if period > pd.Timedelta(minutes=30) and mwhAccepted > 0:
                            constraints = constraints + mwhAccepted
                        else:
                            total_accepted = total_accepted + abs(mwhAccepted)
                            if mwhAccepted > 0:
                                total_increased = total_increased + mwhAccepted
                            else:
                                total_decreased = total_decreased + abs(mwhAccepted)

            except Exception as e:
                print(f"Error fetching bid acceptances for unit {unit.bmUnitName} from {current_start.date()} to {current_end.date()}: {e}")
            
            current_start += pd.Timedelta(weeks=1)

    print(f"Total balancing payments accepted: {total_accepted} MWh")
    print(f"Total balancing payments increased: {total_increased} MWh")
    print(f"Total balancing payments decreased: {total_decreased} MWh")
    print(f"Total constraint payments accepted: {constraints} MWh")