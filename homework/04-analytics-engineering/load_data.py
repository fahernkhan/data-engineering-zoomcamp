import duckdb
import requests
from pathlib import Path

BASE_URL = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download"

PROJECT_DIR = Path("taxi_rides_ny")
DB_PATH = PROJECT_DIR / "taxi_rides_ny.duckdb"
DATA_DIR = Path("data")

def download_csv_files(taxi_type):
    taxi_dir = DATA_DIR / taxi_type
    taxi_dir.mkdir(parents=True, exist_ok=True)

    for year in [2019, 2020]:
        for month in range(1, 13):
            filename = f"{taxi_type}_tripdata_{year}-{month:02d}.csv.gz"
            filepath = taxi_dir / filename

            if filepath.exists():
                print(f"Skipping {filename}")
                continue

            print(f"Downloading {filename}")
            response = requests.get(
                f"{BASE_URL}/{taxi_type}/{filename}",
                stream=True
            )
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

def load_into_duckdb():
    print("Connecting to DuckDB...")
    con = duckdb.connect(str(DB_PATH))

    print("Creating schema prod...")
    con.execute("CREATE SCHEMA IF NOT EXISTS prod")

    for taxi_type in ["yellow", "green"]:
        print(f"Loading {taxi_type} data...")
        con.execute(f"""
            CREATE OR REPLACE TABLE prod.{taxi_type}_tripdata AS
            SELECT *
            FROM read_csv_auto('data/{taxi_type}/*.csv.gz')
        """)

    con.close()
    print("Done loading data.")

if __name__ == "__main__":
    for taxi_type in ["yellow", "green"]:
        download_csv_files(taxi_type)

    load_into_duckdb()
