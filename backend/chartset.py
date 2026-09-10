"""Common `Dataset` base class used to wrap a `DataSource` with stateful,
filterable data and chart-building helpers.

Subclasses typically call `super().__init__(some_data_source)` in their own
`__init__`, then further transform `self.data` as needed.
"""

from dataclasses import dataclass, field
from datasources.datasource import DataBase
import pandas as pd
import plotly.graph_objs as go
from typing import Callable

@dataclass(frozen=True)
class Chart:
    dataset: DataBase
    chart: go.Figure | pd.DataFrame
    title: str = ""
    description: str = ""

    def is_table(self) -> bool:
        return isinstance(self.chart, pd.DataFrame)
    
    def dataset_info(self):
        return self.dataset.source_info()
