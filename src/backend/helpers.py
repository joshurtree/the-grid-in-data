import pandas as pd
import re
from titlecase import titlecase

# Converts dataframe columns from using camel case to capitised words
def camel_case_to_capitalised(df: pd.DataFrame) :
    rename = dict(zip(df.columns, [titlecase(re.sub("([a-z])([A-Z])", r"\1 \2", col)) for col in df.columns]))
    return df.rename(columns=rename)

def snake_case_to_capitalised(df: pd.DataFrame) :
    return df.rename(columns=dict(zip(df.columns, [titlecase(re.sub("_", " ", col)) for col in df.columns])))
