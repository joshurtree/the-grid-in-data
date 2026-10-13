"""Common `Dataset` base class used to wrap a `DataSource` with stateful,
filterable data and chart-building helpers.

Subclasses typically call `super().__init__(some_data_source)` in their own
`__init__`, then further transform `self.data` as needed.
"""

from dataclasses import dataclass, field
from datetime import date
from datasources import DataBase
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go
from typing import Callable, Sequence

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
    chart: go.Figure = field(default_factory=go.Figure)
    title: str = ""
    description: str = ""

    def is_table(self) -> bool:
        """Determine if the chart is a table (i.e., no chart figure is provided)."""
        return self.chart.data == ()
    
    def dataset_info(self):
        return self.dataset.source_info()

@dataclass(frozen=True)
class ChartBuilder:
    dataset: DataBase
    filter_functions: list[Callable[[pd.DataFrame], pd.DataFrame]] | None = None
    title: str = ""
    description: str = ""

    def filter_data(self) -> pd.DataFrame:
        """Filter the dataset based on provided keyword arguments."""
        df = self.dataset.load_data()
        if self.filter_functions:
            for func in self.filter_functions:
                df = func(df)
        return df
    
    def create_table(self) -> Chart:
        """Create a table from the dataset, optionally filtered by provided keyword arguments."""
        table = self.filter_data()
        return Chart(
            dataset=self.dataset,
            table=table,
            chart=go.Figure(),
            title=self.title,
            description=self.description
        )
    
    def add_traces(self, chart: go.Figure, df: pd.DataFrame, x: str, y: Sequence[Trace], stackgroup: str = "", **kwargs) -> go.Figure:
        """Add traces to the provided chart based on the filtered dataset."""
        for y_value in y:
            trace = y_value.add_trace(df, x)
            chart.add_trace(trace, **kwargs)
        return chart
    
    def create_subplots(self, **kwargs) -> Chart:
        """Create an empty chart with no data."""
        return Chart(
            dataset=self.dataset,
            table=self.filter_data(),
            chart=make_subplots(**kwargs),
            title=self.title,
            description=self.description
        )
    
    def create_chart(
        self,
        x: str, 
        y: list[Trace], 
        y_title: str = "",
    ) -> Chart:
        """Create a chart using the provided chart function and store it in the `chart` attribute."""
        table = self.filter_data()

        # Remove all columns from the table that are not in the x or y fields
        table = table[[x] + [trace.y for trace in y]]

        chart = go.Figure(
            layout=go.Layout(
                xaxis_title=x,
                yaxis_title=y_title,
                hovermode="closest"
            )
        )

        chart = self.add_traces(chart, table, x, y)

        return Chart(
            dataset=self.dataset,
            table=table,
            chart=chart,
            title=self.title,
            description=self.description
        )

@dataclass(frozen=True)
class Trace:
    y: str
    hover_template: Callable[[str, str, float|int|str|date, float|int|str|date], str] = default_hover_template
    kwargs: dict = field(default_factory=dict)

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
            hovertemplate=[self.hover_template(x, self.y, x_val, y_val) for x_val, y_val in zip(df[x], df[self.y])],
            **self.kwargs
        )
    
class LineTrace(Trace):
    def add_trace(self, df: pd.DataFrame, x: str) -> go.Scatter:
        """Create a Plotly Line trace for the given DataFrame and x-axis field."""
        return go.Scatter(
            x=df[x],
            y=df[self.y],
            name=self.y,
            mode="lines",
            hovertemplate=[self.hover_template(x, self.y, x_val, y_val) for x_val, y_val in zip(df[x], df[self.y])],
            **self.kwargs
        )

class BarTrace(Trace):
    def add_trace(self, df: pd.DataFrame, x: str) -> go.Bar:
        """Create a Plotly Bar trace for the given DataFrame and x-axis field."""
        return go.Bar(
            x=df[x],
            y=df[self.y],
            name=self.y,
            hovertemplate=[self.hover_template(x, self.y, x_val, y_val) for x_val, y_val in zip(df[x], df[self.y])],
            **self.kwargs
        )
@dataclass(frozen=True)
class AreaTrace(Trace):
    stackgroup: str = ""

    def add_trace(self, df: pd.DataFrame, x: str) -> go.Scatter:
        """Create a Plotly Area trace for the given DataFrame and x-axis field."""
        return go.Scatter(
            x=df[x],
            y=df[self.y],
            name=self.y,
            mode="lines",
            stackgroup=self.stackgroup,
            hovertemplate=[self.hover_template(x, self.y, x_val, y_val) for x_val, y_val in zip(df[x], df[self.y])],
            **self.kwargs
        )
