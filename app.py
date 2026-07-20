"""
GB Electricity Prices - Gradio Web Interface

Reworked to use separate "pages" (sidebar selector toggling page containers)
and to reuse existing module functions where available. Uses zero-arg callable
pattern for safe calls: _safe_call(lambda: module.fn(...))
"""
import gradio as gr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import traceback
import json
from backend.constants import ELEXON_GENERATION_TYPES, NESO_GENERATION_TYPES, RAW_DATA_DIR, TRANSFORMED_DATA_DIR

import backend.gbwep as gbwep
import backend.elecvsgas as elecvsgas
import backend.energy_map as energy_map
import backend.cfd as cfd

from pages.prices import prices_page
from pages.gasvselectricity import evg_page
from pages.energy_map import energy_map_page

with gr.Blocks("GB Energy Generation Map") as app:
    energy_map_page.render()

with app.route("Electricity vs Gas Prices"):
    evg_page.render()

with app.route("GB Energy Wholesale Prices"):
    prices_page.render()

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
