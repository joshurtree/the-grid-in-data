# GB Electricity Prices - Streamlit Web Interface

A web application for analyzing and visualizing GB electricity market data, including wholesale prices, gas prices, and generation locations.

Built with **Streamlit** for interactive data visualization and **Plotly** for charts.

## Features

- **GB Energy Generation Map** — Interactive map showing generator locations and current generation levels
- **Electricity vs Gas Prices** — Compare electricity and gas prices with dual-axis charts and spark gap analysis
- **GB Energy Wholesale Prices** — View wholesale electricity prices over time, colored by generation volume
- **Contracts for Difference** — Analyze CFD payments by technology and strike price

## Quick Start

### Using Nix Flakes (Recommended)

```bash
nix develop                     # Enter dev environment
uv sync                         # Install dependencies
uv run streamlit run app.py     # Start the Streamlit app
```

Access the app at: **http://localhost:8501**

### Using Poetry

```bash
poetry install                  # Install dependencies
poetry run streamlit run app.py
```

### Direct with UV

```bash
uv sync                         # Install dependencies
uv run streamlit run app.py
```

### Using the Nix Flake App

```bash
nix run .#app
```

## Requirements

- Python 3.13+
- Dependencies: streamlit, pandas, plotly, matplotlib, numpy, requests, statsmodels, osgridconverter

## Data Files

The application expects data in the `data/` directory:
- `market-prices.csv` — Wholesale electricity prices
- `gas_prices.csv` — Natural gas prices
- `generators.csv` — Generator locations and metadata
- `tnuosgenzones.geojson` — DNO zone boundaries

## Architecture

- **app.py** — Main Streamlit entrypoint with sidebar navigation between pages
- **pages/** — One module per page, each exposing a `render()` function
- **backend/** — Data loading, filtering, and chart-building logic (framework-agnostic)
- **constants.py** — Configuration and paths
- **pyproject.toml** — Project dependencies (managed by UV or Poetry)

## Notes

- The flake pins to `nixos-unstable` for up-to-date packages
- Data files should be downloaded/fetched using `fetch-data.py` first
- The app runs on `http://0.0.0.0:8501` by default

