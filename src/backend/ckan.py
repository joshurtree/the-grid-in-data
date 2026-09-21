from dataclasses import dataclass
from datetime import time
import pandas as pd
from ckanapi import RemoteCKAN
import requests
from tqdm import tqdm
import time

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
    
    def fetch_extended_data(self, resource_id: str, offset=0, **kwargs) -> pd.DataFrame:
        """
        Fetch all data from the CKAN API using a datastore query, handling pagination.
        """
        all_records = pd.DataFrame()
        limit = self.records_per_request  # CKAN API limit per request
        total_records = self.fetch_record_count(resource_id) - offset
        
        with tqdm(total=total_records, desc=f"Fetching data for resource {resource_id} from {self.base_url}", unit="records") as pbar:
            while True:
                records = self.fetch_data(resource_id, limit=limit, offset=offset, **kwargs)
                all_records = pd.concat([all_records, records], ignore_index=True)
                pbar.update(len(records))
                if len(records) < limit:
                    break  # No more records to fetch

                time.sleep(1)  
                offset += limit

        return pd.DataFrame(all_records)
    
    def fetch_all_resources(self, package_id: str) -> pd.DataFrame:
        """
        Fetch all resources from a CKAN package, handling pagination.
        """
        rc = RemoteCKAN(self.base_url)
        response = rc.action.package_show(id=package_id)
        
        all_records = pd.DataFrame()
        for resource in response["result"]["resources"]:
            if resource["format"].lower() != "csv":
                continue
            all_records = pd.concat([all_records, pd.read_csv(resource["url"])], ignore_index=True)
        
        return all_records
    


@dataclass
class Endpoint:
    resource_id: str
    client: CKANClient

    def __call__(self, offset=0, **kwargs) -> pd.DataFrame:
        return self.client.fetch_extended_data(self.resource_id, offset=offset, **kwargs)

@dataclass
class Package:
    package_id: str
    client: CKANClient

    def __call__(self, **kwargs) -> pd.DataFrame:
        return self.client.fetch_all_resources(self.package_id, **kwargs)

