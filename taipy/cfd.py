import taipy.gui.builder as tgb

with tgb.Page() as cfd_page:
    tgb.text(value="# CFD Payments by Year", mode="md")
    with tgb.part(class_name="card"):
        with tgb.layout(columns="1 1") :
            with tgb.part():
                tgb.selector("{technology}", label="Technology", lov=available_technologies, on_change=update_chart, dropdown=True)
            with tgb.part():
                tgb.selector("{allocation_rounds}", mode="check", label="Allocation Round", lov=allocation_rounds, on_change=update_chart, dropdown=True)
            with tgb.part():
                tgb.toggle(value="{show_table}", label="Show Table", on_change=update_chart)
    with tgb.part(class_name="card"):
        with tgb.part(render="{show_table}", class_name="card", style="margin-top: 10px;"):
            tgb.table("{grouped_data}", title="Total CFD Payments by Financial Year", columns=grouped_data.columns.tolist(), number_format="%.2f", show_all=True)
        with tgb.part(render="{not show_table}", class_name="card", style="margin-top: 10px;"):
            # Create a bar chart using the grouped data
            tgb.chart(
                "{grouped_data}",
                type="bar",
                x="Year",
                y="CFD Payments (£ million)",
                title="Total CFD Payments by Year",
                xaxis_title="Year",
                yaxis_title="CFD Payments (£ million)",
                template="plotly_dark"
            )

