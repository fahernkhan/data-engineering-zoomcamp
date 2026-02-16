import duckdb
import requests
from pathlib import Path

# =====================================================
# CONFIGURATION
# =====================================================

BASE_URL = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download"

PROJECT_DIR = Path("taxi_rides_ny")
DB_PATH = PROJECT_DIR / "taxi_rides_ny.duckdb"
DATA_DIR = Path("data")

YEARS_YELLOW_GREEN = [2019, 2020]
YEAR_FHV = 2019

# =====================================================
# DOWNLOAD FUNCTIONS
# =====================================================

def download_files(taxi_type, years):
    taxi_dir = DATA_DIR / taxi_type
    taxi_dir.mkdir(parents=True, exist_ok=True)

    for year in years:
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

# =====================================================
# LOAD INTO DUCKDB
# =====================================================

def load_into_duckdb():
    print("Connecting to DuckDB...")
    con = duckdb.connect(str(DB_PATH))

    print("Creating schema prod if not exists...")
    con.execute("CREATE SCHEMA IF NOT EXISTS prod")

    # -------------------------
    # Yellow & Green
    # -------------------------
    for taxi_type in ["yellow", "green"]:
        print(f"Loading {taxi_type} data into prod.{taxi_type}_tripdata ...")

        con.execute(f"""
            CREATE OR REPLACE TABLE prod.{taxi_type}_tripdata AS
            SELECT *
            FROM read_csv_auto('data/{taxi_type}/*.csv.gz')
        """)

    # -------------------------
    # FHV (2019 only)
    # -------------------------
    print("Loading fhv data into prod.fhv_tripdata ...")

    con.execute("""
        CREATE OR REPLACE TABLE prod.fhv_tripdata AS
        SELECT *
        FROM read_csv_auto('data/fhv/*.csv.gz')
    """)

    con.close()
    print("All data successfully loaded into DuckDB.")

# =====================================================
# MAIN EXECUTION
# =====================================================

if __name__ == "__main__":
    print("Starting download process...")

    download_files("yellow", YEARS_YELLOW_GREEN)
    download_files("green", YEARS_YELLOW_GREEN)
    download_files("fhv", [YEAR_FHV])

    print("Download complete.")
    load_into_duckdb()
