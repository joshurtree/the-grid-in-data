from taipy.gui import Gui, Icon, navigate
import taipy.gui.builder as tgb
from backend.gbwep import gbwep_page
from backend.cfd import cfd_page
from backend.elecvsgas import elecvsgas_page
from backend.energy_map import generation_map

def change_page(state, action, info):
    navigate(state, info["args"][0])

with tgb.Page() as root:
    tgb.menu(
        label="Menu",
        lov=[
            ("energy_map", "Live Map"),
            ("gbwep", "GB Electricity Prices"),
            ("cfd", "CFD Payments"),
            ("elecvsgas", "Electricity vs Gas Prices")
        ],
        on_action=change_page
    ),
    
pages = {
    '/': root,
    'energy_map': generation_map,
    'gbwep': gbwep_page,
    'cfd': cfd_page,
    'elecvsgas': elecvsgas_page,
}
if __name__ == "__main__":
    Gui(pages=pages).run(run_server=True, title="GB Electricity Prices", dark_mode=True, debug=True, use_reloader=True)
