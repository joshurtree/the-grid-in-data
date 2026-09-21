from dataclasses import dataclass
from altair import value
import numpy as np
import os
import pandas as pd
from constants import DATE_FIELD, METRIC_PATH
from enum import Enum

def get_arrow(value: float) -> str:
    arrows = {
        -1: ":material/arrow_downward:",
        0: ":material/arrow_forward:",
        1: ":material/arrow_upward:"
    }

    return arrows[np.sign(value)]

@dataclass
class MetricUnit:
    prefix: str
    suffix: tuple[str|None, ...]

    def format(self, value: float) -> str:
        zeros = np.floor(np.log10(abs(value))/3) if value > 1 else 0
        suffix_index = int(zeros) if int(zeros) < len(self.suffix) else len(self.suffix) - 1
        #print(f"Formatting value: {value}, zeros: {zeros}, suffix_index: {suffix_index}")
        suffix = self.suffix[suffix_index]
        if suffix is not None:
            return f"{self.prefix}{value/10**(3*suffix_index):,.2f} {suffix}"
        return f"{self.prefix}{value:,.2f}"

CURRENCY = MetricUnit(prefix="£", suffix=(None, None, "Million", "Billion"))
POWER = MetricUnit(prefix="", suffix=("MW", "GW"))
ENERGY = MetricUnit(prefix="", suffix=("MWh", "GWh", "TWh"))
UNIT_PRICE = MetricUnit(prefix="£", suffix=("per MWh",))
PERCENT = MetricUnit(prefix="", suffix=("%",))
DAYS = MetricUnit(prefix="", suffix=("Days",))
NO_UNIT = MetricUnit(prefix="", suffix=(None,))

@dataclass
class Metric:
    name: str
    unit: MetricUnit
    description: str = ""
    current: float = 0.0
    annual_change: float = 0.0
    change_from_5_years_ago: float = 0.0

    def save(self) -> None:
        metric_data = {
            "current": self.current,
            "annual_change": self.annual_change,
            "change_from_5_years_ago": self.change_from_5_years_ago
        }
        pd.DataFrame([metric_data]).to_json(os.path.join(METRIC_PATH, f"{self.name}.json"), orient='records', indent=2)
    
    def value_with_unit(self) -> str:
        return self.unit.format(self.current)
    
    
    def change(self) -> str:
        format_change = lambda x: f"{get_arrow(x)} {x:,.2f}%"
        return f"{format_change(self.annual_change)} {format_change(self.change_from_5_years_ago)}"

    def __post_init__(self) -> None:
        metric_file = os.path.join(METRIC_PATH, f"{self.name}.json")
        if not os.path.exists(metric_file):
            print(f"Warning: Metric file {metric_file} does not exist.")
            return
        
        metric_data = pd.read_json(metric_file).iloc[0].to_dict()
        self.current = metric_data["current"]
        self.annual_change = metric_data["annual_change"]
        self.change_from_5_years_ago = metric_data["change_from_5_years_ago"]
        