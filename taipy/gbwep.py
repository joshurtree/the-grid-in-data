import pandas as pd
import plotly.graph_objects as go
from taipy.gui import Gui
import taipy.gui.builder as tgb
from backend.constants import NESO_GENERATION_TYPES, TRANSFORMED_DATA_DIR

target_generation: str = "LOW_CARBON"
minimum_usage: int = 0
start_date: date = date.today() - pd.DateOffset(years=1)  # Default to one year ago
end_date: date = date.today()
date_range = [start_date, end_date]
show_table: bool = False
maximum_usage: int = 100
(chart_figure, maximum_usage) = create_chart(start_date, end_date, target_generation, minimum_usage)
(table, maximum_usage) = group_by_generation(start_date, end_date, target_generation, minimum_usage)

def update_gbwep_chart(state):
    if not state.show_table:
        (state.chart_figure, state.maximum_usage) = create_chart(state.date_range[0], state.date_range[1], state.target_generation, state.minimum_usage)
    else:
        (state.table, state.maximum_usage) = group_by_generation(state.date_range[0], state.date_range[1], state.target_generation, state.minimum_usage)
    
with tgb.Page() as gbwep_page:
    tgb.text(value="# GB Electricity Prices", mode="md")
    with tgb.part(class_name="card"):
        tgb.selector("{target_generation}", label="Target Generation Type", lov=list(NESO_GENERATION_TYPES.items()), on_change=update_gbwep_chart, dropdown=True)
        with tgb.layout(columns="2 1"):
            # with tgb.part():
            #     tgb.date("{start_date}", label="Start Date", min=date(2016, 6, 30), max=date.today(), format='dd/MM/yyyy', on_change=update_chart, layout=tgb.layout(width="20%"))
            # with tgb.part():
            #     tgb.date("{end_date}", label="End Date", min=date(2016, 6, 30), max=date.today(), format='dd/MM/yyyy', on_change=update_chart, layout=tgb.layout(width="20%"))
            with tgb.part():
                tgb.date_range("{date_range}", label="Date Range", min=date(2016, 6, 30), max=date.today(), format='dd/MM/yyyy', on_change=update_gbwep_chart, layout=tgb.layout(width="40%"))
            with tgb.part():
                tgb.toggle(value="{show_table}", label="Show Table", on_change=update_gbwep_chart)
        with tgb.layout(columns="1 3"):
            with tgb.part():
                tgb.text(value=f"Filter by minimum target generation (%)", mode="md")
            with tgb.part():
                tgb.slider("{minimum_usage}", label=f"Minimum target generation (%)", min=0, max="{maximum_usage}", on_change=update_gbwep_chart, layout=tgb.layout(width="40%"))                
    with tgb.part(class_name="card"):
        with tgb.part(render="{not show_table}"):
            tgb.chart(figure="{chart_figure}", title=f"Wholesale Price vs Date", xaxis_title="Date", yaxis_title="Price (£/MWh)", hovermode="closest", template="plotly_dark")
        with tgb.part(render="{show_table}"):
            tgb.table("{table}", title="Average Generation by Price Group", columns=table.columns.tolist(), number_format="%.2f", show_all=True)
    with tgb.part(class_name="card"):
        tgb.text(value="## Notes", mode="md")
        tgb.text(value="- Generation data is sourced from [Neso](https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/resource/f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv).", mode="md")
        tgb.text(value="- Price data is sourced from the [Low Carbon Contracts Company](https://dp.lowcarboncontracts.uk/dataset/19f1ebee-93b7-4ef4-9465-bba50fa4ad06/resource/866e6a4e-86c7-411e-9464-2ac3ad56ae35/download/imrp_actuals.csv).", mode="md")
        tgb.text(value="- Chart inspired by [Ember](https://ember-energy.org/latest-insights/british-power-prices-are-increasingly-independent-from-gas/).", mode="md")
        tgb.text(value="- The chart shows the average wholesale price per day, colored by the percentage of the selected generation type.", mode="md")
        tgb.text(value="- The table below shows the average generation and cost for each generation type over the selected date range.", mode="md")

