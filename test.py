import requests
import pandas as pd
from bs4 import BeautifulSoup

def scrape_uk_gas_forecast():
    """Fetch the page at `url` and return the second HTML table as a pandas DataFrame.

    Strategy:
    - Try pandas.read_html on the response text (fast and convenient).
    - If pandas finds >=2 tables, return the second one (index 1).
    - If no/one table found, optionally fall back to BeautifulSoup-based parsing if available.

    Args:
        url: Page URL to scrape (defaults to the poundf UK natural gas page).
        session: Optional requests-like session with a .get() method.

    Returns:
        pandas.DataFrame for the second table (or the only table found).

    Raises:
        requests.HTTPError for non-2xx responses.
        RuntimeError if no table can be parsed (or bs4 is required but missing).
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get("https://poundf.co.uk/uk-natural-gas", headers=headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    tgs = soup.find_all("table")
    if len(tgs) < 2:
        raise RuntimeError(f"Not enough <table> elements ({len(tgs)}) found on the page")
    target = tgs[1]

    rows = []
    year = None
    for tr in target.find_all("tr"):
        cols = [cell.get_text(strip=True) for cell in tr.find_all(["th", "td"])]

        if len(cols) == 1:
            # Year header row, extract year
            year = cols[0]
        elif year is not None:
            # Data row, prepend year to the first column
            cols[0] = f"{year}-{cols[0]}"
            rows.append(cols[:2])

    if not rows:
        return pd.DataFrame()

    data = pd.DataFrame(rows, columns=["Date", "Price"])
    data["Date"] = pd.to_datetime(data["Date"], format="%Y-%b", errors="coerce")
    data["Price"] = pd.to_numeric(data["Price"], errors="coerce")
    return data

print(scrape_uk_gas_forecast())