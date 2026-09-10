import pandas as pd
from backend.chartset import ChartSet
from datasources.system import generation_source, total_capacity_source

class CapacityFactorsData(ChartSet):
    def __init__(self):
        super().__init__(generation_source)
        self.capacity_data = total_capacity_source.load_data()
        self.capacity_data['capacity'] = pd.to_numeric(self.capacity_data['capacity'], errors='coerce')
        self.capacity_data.dropna(subset=['capacity'], inplace=True)