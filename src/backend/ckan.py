from dataclasses import dataclass
from datetime import datetime, time
import os
import pandas as pd
from ckanapi import RemoteCKAN
import requests
from tqdm import tqdm
import time

from constants import CACHED_DATA_PATH
from datasources.datasource import DataSource

@dataclass
class CKANClient:
    base_url: str
    records_per_request: int = 100  # Default number of records to fetch per request

    def __post_init__(self):
        self.rc = RemoteCKAN(self.base_url)

    def list_packages(self) -> pd.DataFrame:
        """
        List all packages available in the CKAN instance.
        """
        packages = self.rc.action.package_list()
        return pd.DataFrame(packages, columns=["package_id"])
    
    def fetch_data(self, resource_id: str, **kwargs) -> pd.DataFrame:
        """
        Fetch data from the CKAN API using a datastore query.
        """
        #print(f"Fetching data for resource {resource_id} from {self.base_url} with parameters: {kwargs}")
        response = self.rc.action.datastore_search(resource_id=resource_id, **kwargs)
        if "records" not in response:
            print(f"No records found for resource {resource_id}. Response: {response}")
            return pd.DataFrame()  # Return an empty DataFrame if no records are found
        
        return pd.DataFrame(response["records"])
    
    def fetch_record_count(self, resource_id: str) -> int:
        """
        Fetch the total number of records for a given resource.
        """
        response = self.rc.action.datastore_search(resource_id=resource_id, limit=0)
        return response["total"]

    def fetch_extended_data(self, resource_id: str, **kwargs) -> pd.DataFrame:
        """
        Fetch all data from the CKAN API using a datastore query, handling pagination.
        """
        # Check if cached data exists
        cache_path = os.path.join(CACHED_DATA_PATH, f"{resource_id}.parquet")
        total_records = self.fetch_record_count(resource_id)
        all_records = pd.DataFrame()

        try:
            all_records = pd.read_parquet(cache_path)
            if not all_records.empty and len(all_records) == total_records:
                print(f"Loaded cached data for resource {resource_id} from cache. Total records: {len(all_records)}")
                return all_records
            offset = len(all_records)  # Continue fetching from where the cache left off
        except FileNotFoundError:
            print(f"No cached data found for resource {resource_id}. Fetching from CKAN API...")
            offset = 0  # Start from the beginning if no cache exists

        limit = self.records_per_request  # CKAN API limit per request
        
        with tqdm(total=total_records-offset, desc=f"Fetching data for resource {resource_id} from {self.base_url}", unit="records") as pbar:
            fail_count = 0
            while True:
                try:
                    records = self.fetch_data(resource_id, limit=limit, offset=offset, **kwargs)
                    all_records = pd.concat([all_records, records], ignore_index=True)
                    pbar.update(len(records))
                    if len(records) < limit:
                        break  # No more records to fetch

                    time.sleep(1)  
                    offset += limit
                    fail_count = 0  # Reset fail count on successful fetch
                except requests.exceptions.RequestException as e:
                    print(f"Request failed: {e}. Retrying in 60 seconds...")
                    time.sleep(60)  # Wait before retrying
                    fail_count += 1
                    if fail_count >= 5:
                        print("Failed to fetch data after 5 attempts. Exiting.")
                        break

        # Cache the fetched data to a local file for future use
        all_records.to_parquet(cache_path, index=False, compression='zstd', compression_level=9)
        return pd.DataFrame(all_records)

    def fetch_all_resources(self, package_id: str, offset: int = 0, **kwargs) -> pd.DataFrame:
        """
        Fetch all resources from a CKAN package, handling pagination.
        """
        rc = RemoteCKAN(self.base_url)
        response = rc.action.package_show(id=package_id)
        running_offset = offset

        all_records = pd.DataFrame()
        for resource in response["resources"]:
            if not resource["datastore_active"]:
                continue

            data_length = self.fetch_record_count(resource["id"])
            if data_length <= running_offset:
                running_offset -= data_length
                continue  # Skip this resource if the offset exceeds the data length

            all_records = pd.concat([all_records, self.fetch_extended_data(resource["id"], **kwargs)], ignore_index=True)
            running_offset = 0  # Reset offset after the first resource

        return all_records
    

@dataclass
class Endpoint:
    resource_id: str
    client: CKANClient

    def __call__(self, **kwargs) -> pd.DataFrame:
        return self.client.fetch_extended_data(self.resource_id, **kwargs)

@dataclass
class Package:
    package_id: str
    client: CKANClient

    def __call__(self, **kwargs) -> pd.DataFrame:
        return self.client.fetch_all_resources(self.package_id, **kwargs)

