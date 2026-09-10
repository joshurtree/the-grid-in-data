from dataclasses import dataclass
import numpy as np
import os
import pandas as pd
from backend.constants import DATE_FIELD, METRIC_PATH

@dataclass
class Metric:
    name: str
    unit: str
    last_12_months: float
    annual_change: float
    change_from_5_years_ago: float

    def save(self) -> None:
        metric_data = {
            "name": self.name,
            "unit": self.unit,
            "last_12_months": self.last_12_months,
            "annual_change": self.annual_change,
            "change_from_5_years_ago": self.change_from_5_years_ago
        }
        pd.DataFrame([metric_data]).to_json(os.path.join(METRIC_PATH, f"{self.name}.json"), orient='records', indent=2)
    
    @staticmethod
    def load(metric_name: str) -> 'Metric':
        metric_file = os.path.join(METRIC_PATH, f"{metric_name}.json")
        if not os.path.exists(metric_file):
            raise FileNotFoundError(f"Metric file {metric_file} does not exist.")
        metric_data = pd.read_json(metric_file).iloc[0].to_dict()
        return Metric(
            name=metric_data["name"],
            unit=metric_data["unit"],
            last_12_months=metric_data["last_12_months"],
            annual_change=metric_data["annual_change"],
            change_from_5_years_ago=metric_data["change_from_5_years_ago"]
        )
    
    @staticmethod
    def create_metric(metric_name: str, unit: str, df: pd.DataFrame, metric_column: str) -> Metric:
        '''
        Input: A dataframe with a 'Metric' column and a 'Date' column
        '''
        get_offset = lambda months: pd.Timestamp.now() - pd.DateOffset(months=months)
        last_12_months = df[(df[DATE_FIELD] >= get_offset(13)) & (df[DATE_FIELD] <= get_offset(1))]
        previous_year = df[(df[DATE_FIELD] >= get_offset(25)) & (df[DATE_FIELD] <= get_offset(13))]
        five_years_ago = df[(df[DATE_FIELD] >= get_offset(61)) & (df[DATE_FIELD] <= get_offset(49))]

        # Create the metric DataFrame
        last_12_months_metric = last_12_months[metric_column].sum()
        previous_year_metric = previous_year[metric_column].sum()
        five_years_ago_metric = five_years_ago[metric_column].sum()
        calc_change = lambda current, previous: (current - previous) / previous * 100 if previous != 0 else np.nan
        cost_metric = Metric(
            name=metric_name,
            unit=unit,
            last_12_months=last_12_months_metric,
            annual_change=calc_change(last_12_months_metric, previous_year_metric),
            change_from_5_years_ago=calc_change(last_12_months_metric, five_years_ago_metric)
        )

        return cost_metric
