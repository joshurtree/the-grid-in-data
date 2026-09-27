"""Common `Dataset` base class used to wrap a `DataSource` with stateful,
filterable data and chart-building helpers.

Subclasses typically call `super().__init__(some_data_source)` in their own
`__init__`, then further transform `self.data` as needed.
"""

from dataclasses import dataclass, field
from datetime import date
from platform import processor
from datasources import DataBase
import pandas as pd
import plotly.graph_objs as go
from typing import Callable

def process_value(value: float|int|str|date) -> str:
    """Process a value to ensure it is a float, handling strings with commas."""
    if isinstance(value, float):
        return f"{value:.2f}"
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, date):
        return value.strftime("%d %B %Y")
    
    return value

def default_hover_template(x_field: str, y_field: str, x: float|int|str|date, y: float|int|str|date) -> str:
    """Default hover template for Plotly charts."""
    return f"{x_field}: {process_value(x)}<br>{y_field}: {process_value(y)}<extra></extra>"

@dataclass(frozen=True)
class Chart:
    dataset: DataBase
    table: pd.DataFrame = field(default_factory=pd.DataFrame)
    chart: go.Figure | None = None
    title: str = ""
    description: str = ""

    def is_table(self) -> bool:
        """Determine if the chart is a table (i.e., no chart figure is provided)."""
        return self.chart is None
    
    def dataset_info(self):
        return self.dataset.source_info()


@dataclass(frozen=True)
class Trace:
    y: str
    hover_template: Callable[[str, str, float|int|str|date, float|int|str|date], str] = default_hover_template

    def add_trace(self, df: pd.DataFrame, x: str) -> go.Scatter:
        raise NotImplementedError("Subclasses must implement the add_trace method.")

class ScatterTrace(Trace):
    def add_trace(self, df: pd.DataFrame, x: str) -> go.Scatter:
        """Create a Plotly Scatter trace for the given DataFrame and x-axis field."""
        return go.Scatter(
            x=df[x],
            y=df[self.y],
            name=self.y,
            mode="markers",
            hovertemplate=[self.hover_template(x, self.y, x_val, y_val) for x_val, y_val in zip(df[x], df[self.y])]
        )
    
class LineTrace(Trace):
    def add_trace(self, df: pd.DataFrame, x: str) -> go.Scatter:
        """Create a Plotly Line trace for the given DataFrame and x-axis field."""
        return go.Scatter(
            x=df[x],
            y=df[self.y],
            name=self.y,
            mode="lines",
            hovertemplate=[self.hover_template(x, self.y, x_val, y_val) for x_val, y_val in zip(df[x], df[self.y])]
        )

class BarTrace(Trace):
    def add_trace(self, df: pd.DataFrame, x: str) -> go.Bar:
        """Create a Plotly Bar trace for the given DataFrame and x-axis field."""
        return go.Bar(
            x=df[x],
            y=df[self.y],
            name=self.y,
            hovertemplate=[self.hover_template(x, self.y, x_val, y_val) for x_val, y_val in zip(df[x], df[self.y])]
        )
    
def create_chart(
    df: pd.DataFrame, 
    x: str, 
    y: list[Trace], 
    y_title: str = "",
) -> go.Figure:
    """Create a chart using the provided chart function and store it in the `chart` attribute."""
    chart = go.Figure(
        layout=go.Layout(
            xaxis_title=x,
            yaxis_title=y_title,
        )
    )

    for y_value in y:
        chart.add_trace(y_value.add_trace(df, x))

    return chart