def do_update_chart(state):
    data = create_data(state.time, state.fossil_fuel_types + state.low_carbon_types + state.other_types)
    state.chart_figure = update_chart(data)

def do_show_generator_details(state):
    if len(state.selected_generator) == 0:
        return
    generator_info = state.data.iloc[state.selected_generator[-1]].to_dict('records')[0]
    state.generator_details = f"## {generator_info['name']}\n"
    state.generator_details += f"| **Fuel Type** | {ELEXON_GENERATION_TYPES[generator_info['fuel_type']]} |\n"
    state.generator_details += f"| **Latitude** | {generator_info['lat']} |\n"
    state.generator_details += f"| **Longitude** | {generator_info['lon']} |\n"
    state.generator_details += f"| **Current Generation** | {generator_info['current_generation']:.2f} MW |\n"
    #state.generator_details += f"**BMU IDs: {', '.join(generator_info['elexonBmUnit'])}\n"
    state.show_generator_details = True

fossil_fuel_types = GENERATION_SUPER_GROUPS['Fossil Fuels']
low_carbon_types = GENERATION_SUPER_GROUPS['Low Carbon']
other_types = GENERATION_SUPER_GROUPS['Other'] 
selected_generator = []
generator_details = ""
show_generator_details = False
time = datetime.now()
data = create_data(time, fossil_fuel_types + low_carbon_types + other_types)
chart_figure = update_chart(data)

def get_generator_types(group):
    return [(fuel_type, ELEXON_GENERATION_TYPES[fuel_type]) for fuel_type in GENERATION_SUPER_GROUPS[group]]
