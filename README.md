# GB Electricity Prices - Gradio Web Interface

A web application for analyzing and visualizing GB electricity market data, including wholesale prices, gas prices, and generation locations.

Built with **Gradio** for interactive data visualization and **Plotly** for charts.

## Features

- **Electricity Prices Tab** — View wholesale electricity prices over time, colored by renewable energy percentage
- **Electricity vs Gas Tab** — Compare electricity and gas prices with dual-axis charts
- **Energy Map Tab** — Interactive map showing generator locations and DNO zone boundaries

## Quick Start

### Using Nix Flakes (Recommended)

```bash
nix develop          # Enter dev environment
uv sync              # Install dependencies
uv run app.py        # Start the Gradio app
```

Access the app at: **http://localhost:7860**

### Using Poetry

```bash
poetry install       # Install dependencies
poetry run python app.py
```

### Direct with UV

```bash
uv sync              # Install dependencies
uv run app.py
```

### Using the Nix Flake App

```bash
nix run .#app
```

## Requirements

- Python 3.12+
- Dependencies: gradio, pandas, plotly, matplotlib, numpy, requests, statsmodels, osgridconverter

## Data Files

The application expects data in the `data/` directory:
- `market-prices.csv` — Wholesale electricity prices
- `gas_prices.csv` — Natural gas prices
- `generators.csv` — Generator locations and metadata
- `tnuosgenzones.geojson` — DNO zone boundaries

## Architecture

- **app.py** — Main Gradio application with three tabs
- **constants.py** — Configuration and paths
- **pyproject.toml** — Project dependencies (managed by UV or Poetry)

## Notes

- The flake pins to `nixos-unstable` for up-to-date packages
- Data files should be downloaded/fetched using `fetch-data.py` first
- The app runs on `http://0.0.0.0:7860` by default
