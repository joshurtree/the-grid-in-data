
from io import BytesIO
import os
import pandas as pd
import requests

# Point OpenSSL at certifi's CA bundle. Some Python builds (e.g. the portable
# CPython downloaded by `uv`) don't have a system CA bundle wired up, which
# causes `ssl.SSLCertVerificationError: unable to get local issuer
# certificate` when fetching data over HTTPS.
os.environ.setdefault("SSL_CERT_FILE", __import__("certifi").where())

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch_from_url(url: str, params: dict | None = None, headers: dict | None = None) -> bytes:
    """Fetch data from a URL and return the content as a DataFrame."""
    if headers is None:
        headers = DEFAULT_HEADERS
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    if not response.content or response.content.strip() == b'':
        print(f"Warning: Received empty response from {url}.")
        return b''
    return response.content
