# The Grid in Data

A website for analyzing and visualizing GB electricity grid data, including wholesale prices, gas prices, generation locations, capacity factors and
more. 

Built with **Streamlit** for interactive data visualization and **Plotly** for charts.

## Features


## Quick Start
```bash
nix develop                     # Enter dev environment (if using Nix)
uv sync                         # Install dependencies
uv run streamlit run app.py     # Start the Streamlit app
uv run fetch-data.py            # Fetches and processed data for use in the website
```

## Requirements

- Python 3.13+
- Dependencies: streamlit, pandas, plotly, matplotlib, numpy, requests, statsmodels, osgridconverter

## Data Files

The application expects data in the `data/` directory in the following structure:
- data/raw - Raw data files fetched from external sources
- data/processed - Processed data files ready for analysis and visualization
- data/manual - Any manually curated data files
- data/metrics - Files used for displaying metrics
## Architecture

- **src/app.py** — Main Streamlit entrypoint with sidebar navigation between pages
- **src/fetch-data.py** — Script for fetching and processing data for the website
- **src/pages/** — One module per page, each exposing a `render()` function
- **src/backend/** — Data loading, filtering, and chart-building (using plotly) logic (framework-agnostic)
- **src/constants.py** — Configuration and paths
- **pyproject.toml** — Project dependencies (managed by UV or Poetry)

## Notes

- The flake pins to `nixos-unstable` for up-to-date packages
- Data files should be downloaded/fetched using `fetch-data.py` first
- The app runs on `http://0.0.0.0:8501` by default

