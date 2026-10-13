from collections.abc import Callable
import pandas as pd
import re
from titlecase import titlecase

def create_exclude_lambda(exclude: list[str]) -> Callable:
    return lambda word, **kwargs: word if word in exclude else None

# Converts dataframe columns from using camel case to capitised words
def camel_case_to_capitalised(df: pd.DataFrame, exclude: list[str] = []) -> pd.DataFrame:
    rename = dict(zip(df.columns, [titlecase(re.sub("([a-z])([A-Z])", r"\1 \2", col), create_exclude_lambda(exclude)) for col in df.columns]))
    return df.rename(columns=rename)

def snake_case_to_capitalised(df: pd.DataFrame, exclude: list[str] = []) -> pd.DataFrame:
    return df.rename(columns=dict(zip(df.columns, [titlecase(re.sub("_", " ", col), create_exclude_lambda(exclude)) for col in df.columns])))
