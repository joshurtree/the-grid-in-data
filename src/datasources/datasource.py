from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
import os
import pandas as pd
from typing import Tuple

from constants import RAW_DATA_PATH, PROCESSED_DATA_PATH

class DataCategory(Enum):
    GENERAL="general"
    SYSTEM="system"
    POLICY="policy"
    GAS="gas"
    SECURITY="security"


@dataclass
class DataProvider:
    name: str
    url: str
    short_name: str =  ""

    def __post_init__(self):
        if self.short_name == "":
            self.short_name = self.name

    def markdown_link(self):
        return f"[{self.short_name}]({self.url})"

self_provider = DataProvider(name="Self", url="")

@dataclass
class DataBase:
    name: str
    category: DataCategory
    date_fields: list[str] = field(default_factory=lambda: ["Date"])

    def exists(self) -> bool:
        return os.path.exists(self.path())

    def load_data(self) -> pd.DataFrame:
        return pd.read_parquet(self.path())

    def save_data(self, data) -> None:
        # ensure the directory exists
        os.makedirs(os.path.dirname(self.path()), exist_ok=True)

        data.to_parquet(self.path(), index=False)
        
    def path(self) -> str:
        raise NotImplementedError("Subclasses must implement the path() method.")
    
    def extension(self) -> str:
        return "parquet"

    def raw_source_info(self) -> list[str]:
        raise NotImplementedError("Subclasses must implement the source_info() method.")
    
    def source_info(self) -> str:
        provider_links = list(set(self.raw_source_info()))
        return f"Source{'s' if len(provider_links) > 1 else ''}: {', '.join(provider_links)}"

    
@dataclass
class DataSource(DataBase):
    providers: list[DataProvider] = field(default_factory=lambda: [self_provider])
    url: str = ""

    def get_providers(self) -> list[DataProvider]:
        return self.providers

    def fetch_data(self, fetch_func=pd.read_csv) -> pd.DataFrame:
        data = fetch_func(self.url)
        self.save_data(data)
        return data

    def path(self) -> str:
        return os.path.join(RAW_DATA_PATH, self.category.value, self.name) + f".{self.extension()}"

    def raw_source_info(self) -> list[str]:
        return [provider.markdown_link() for provider in self.get_providers()]

@dataclass
class DataSet(DataBase):
    datasources: list[DataBase] = field(default_factory=list)

    def base_data(self) -> Tuple[pd.DataFrame, ...]:
        return tuple([data.load_data() for data in self.datasources])

    def path(self) -> str:
        return os.path.join(PROCESSED_DATA_PATH, self.category.value, self.name) + f".{self.extension()}"

    def raw_source_info(self) -> list[str]:
        return [link for ds in self.datasources for link in ds.raw_source_info()]