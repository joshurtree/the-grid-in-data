from taipy.gui import Gui
import taipy.gui.builder as tgb

start_date: date = date.today() - pd.DateOffset(years=1)  # Default to one year ago
end_date: date = date.today()
date_range = [start_date, end_date]
show_ratio: bool = False
period_group: str = 'Day'
chart_figure: go.Figure = create_chart(start_date, end_date, period_group)

def update_chart(state):
    chart_function = create_chart if not state.show_ratio else ratio_chart
    state.chart_figure = chart_function(state.date_range[0], state.date_range[1], state.period_group)
    #state.table = group_by_generation(data[(data['DATETIME'] >= pd.to_datetime(state.start_date)) & (data['DATETIME'] <= pd.to_datetime(state.end_date))])

with tgb.Page() as elecvsgas_page:
    tgb.text(value="# GB Electricity Prices vs Gas Prices", mode="md")
    with tgb.part(class_name="card"):
        tgb.date_range("{date_range}", label="Date Range", min=date(2016, 6, 30), max=date.today(), format='dd/MM/yyyy', on_change=update_chart)
        with tgb.layout(columns="1 1"):
            with tgb.part():
                tgb.selector("{period_group}", label="Group By", lov=list(PERIOD_GROUPS.keys())[1:], on_change=update_chart, dropdown=True)
            with tgb.part():
                tgb.toggle(value="{show_ratio}", label="Show Ratio", on_change=update_chart)
    with tgb.part(class_name="card"):
        #with tgb.part(render="{not show_table}"):
        tgb.chart(figure="{chart_figure}", title=f"Wholesale Electricity Price vs Gas Price", xaxis_title="Date", yaxis_title="Price (£/MWh)", hovermode="closest", template="plotly_dark")
        #with tgb.part(render="{show_table}"):
        #    tgb.table("{table}", title="Average Generation by Price Group", columns=table.columns.tolist(), number_format="%.2f", show_all=True)
    with tgb.part(class_name="card"):
        tgb.text(value="## Data Source", mode="md")
        tgb.text(value="Electricity prices are sourced from the [Elexon Portal](https://www.elexonportal.co.uk/), while gas prices are sourced from the ONS's [System Average Price of Gas](https://www.ons.gov.uk/economy/economicoutputandproductivity/output/datasets/systemaveragepricesapofgas).", mode="md")