# Load all the json files in the data directory and its subdirectories and convert to using paraquet format. This is a one-time operation to improve performance and reduce file size.
import pandas as pd
import os

def convert_json_to_parquet(json_dir):
    for root, dirs, files in os.walk(json_dir):
        for file in files:
            if file.endswith('.json'):
                json_path = os.path.join(root, file)
                parquet_path = json_path.replace('.json', '.parquet')

                # Load the JSON file and save as Parquet
                df = pd.read_json(json_path)
                # Detect date columns and convert them to datetime
                for col in df.columns:
                    if 'date' in col.lower() or 'time' in col.lower():
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        
                df.to_parquet(parquet_path, index=False)
                print(f"Converted {json_path} to {parquet_path}")

convert_json_to_parquet('data')
