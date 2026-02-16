# 📘 Module 4 Homework: Analytics Engineering with dbt – Complete Documentation

## 🎯 Objective

The goal of this homework is to apply **Analytics Engineering** principles using **dbt (data build tool)** with a local **DuckDB** data warehouse. We transform NYC taxi trip data (Yellow, Green, and FHV) into analytical models to answer business questions and understand dbt’s core features.

---

## 🧰 Tools & Technologies

- **Python 3.9+** – for data loading script
- **dbt-core** & **dbt-duckdb** – transformation tool and DuckDB adapter
- **DuckDB** – embedded columnar database, acting as our data warehouse
- **Dataset**: NYC TLC trip data (Yellow 2019–2020, Green 2019–2020, FHV 2019) – sourced from [DataTalksClub releases](https://github.com/DataTalksClub/nyc-tlc-data/releases)

---

## 🧱 Step 1: Environment Setup

### 1.1 Create and activate a virtual environment

```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 1.2 Install dbt and DuckDB adapter

```bash
pip install dbt-duckdb
```

Verify installation:

```bash
dbt --version
```

You should see versions for dbt-core and dbt-duckdb.

---

## ⚙️ Step 2: Configure dbt Profile

dbt needs a connection to your warehouse. Create a `profiles.yml` file in the default directory (`~/.dbt/` on Linux/macOS, `C:\Users\<user>\.dbt\` on Windows).

**Final `profiles.yml`:**

```yaml
taxi_rides_ny:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: taxi_rides_ny/taxi_rides_ny.duckdb
      schema: dev
      threads: 1
      extensions:
        - parquet
      settings:
        memory_limit: '2GB'
        preserve_insertion_order: false
    prod:
      type: duckdb
      path: taxi_rides_ny/taxi_rides_ny.duckdb
      schema: prod
      threads: 1
      extensions:
        - parquet
      settings:
        memory_limit: '2GB'
        preserve_insertion_order: false
```

**Explanation:**

- **target: dev** – default target, but we'll explicitly use `--target prod` for homework.
- **path** – location of the DuckDB database file.
- **schema** – separate schemas for development and production to avoid interference.
- **threads** – number of concurrent threads; set to 1 to avoid overwhelming laptop resources.
- **extensions** – load Parquet extension to read/write Parquet files if needed.
- **settings.memory_limit** – crucial for large datasets (>2GB) to prevent out‑of‑memory errors.
- **preserve_insertion_order: false** – improves aggregation performance.

Test the connection:

```bash
dbt debug
```

Expected output: `All checks passed!`

---

## 📥 Step 3: Download and Load Raw Data

We use a Python script to download 48 CSV files (Yellow & Green for 2019‑2020, FHV for 2019) and load them into DuckDB.

### 3.1 Script `load_data.py`

```python
import duckdb
import requests
from pathlib import Path

BASE_URL = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download"
PROJECT_DIR = Path("taxi_rides_ny")
DB_PATH = PROJECT_DIR / "taxi_rides_ny.duckdb"
DATA_DIR = Path("data")

YEARS_YELLOW_GREEN = [2019, 2020]
YEAR_FHV = 2019

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
            response = requests.get(f"{BASE_URL}/{taxi_type}/{filename}", stream=True)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

def load_into_duckdb():
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS prod")
    for taxi_type in ["yellow", "green"]:
        print(f"Loading {taxi_type} data into prod.{taxi_type}_tripdata ...")
        con.execute(f"""
            CREATE OR REPLACE TABLE prod.{taxi_type}_tripdata AS
            SELECT * FROM read_csv_auto('data/{taxi_type}/*.csv.gz')
        """)
    print("Loading fhv data into prod.fhv_tripdata ...")
    con.execute("""
        CREATE OR REPLACE TABLE prod.fhv_tripdata AS
        SELECT * FROM read_csv_auto('data/fhv/*.csv.gz')
    """)
    con.close()
    print("All data successfully loaded into DuckDB.")

if __name__ == "__main__":
    download_files("yellow", YEARS_YELLOW_GREEN)
    download_files("green", YEARS_YELLOW_GREEN)
    download_files("fhv", [YEAR_FHV])
    load_into_duckdb()
```

**Explanation:**

- **download_files** – downloads monthly CSV.GZ files for each taxi type, skipping already downloaded files.
- **load_into_duckdb** – connects to DuckDB, creates the `prod` schema, and uses `read_csv_auto` to read all matching files into a table. This creates raw tables: `prod.yellow_tripdata`, `prod.green_tripdata`, `prod.fhv_tripdata`.

### 3.2 Run the script

```bash
python load_data.py
```

After completion, verify the database file exists and its size:

```bash
ls -lh taxi_rides_ny/taxi_rides_ny.duckdb
# Should be > 2.6 GB
```

---

## 🔨 Step 4: Build dbt Models

### 4.1 Navigate to the dbt project

```bash
cd taxi_rides_ny
```

### 4.2 Install dbt dependencies

The project uses `dbt_utils` and `codegen`. Install them:

```bash
dbt deps
```

### 4.3 Run all models (build)

```bash
dbt build --target prod
```

This command:

- Runs all models (staging, intermediate, facts, dimensions)
- Executes seeds (if any)
- Runs tests defined in `schema.yml`
- Uses the `prod` target, placing models in the `prod` schema

**Expected outcome:** All steps succeed with no errors.

### 4.4 Understanding the model lineage

The DAG (directed acyclic graph) of this project is:

```
Raw Tables (prod.yellow_tripdata, prod.green_tripdata)
    ↓
Staging: stg_yellow_tripdata, stg_green_tripdata
    ↓
Intermediate: int_trips_unioned (union of yellow & green)
    ↓
int_trips (joins with dim_zones)
    ↓
fct_trips (fact table)
    ↓
fct_monthly_zone_revenue (monthly aggregation per zone)
```

Each model uses `{{ ref('model_name') }}` to refer to upstream models, enabling dbt to build the dependency graph.

---

## ✅ Answering the Homework Questions

Now we query the models directly in DuckDB. Open the DuckDB CLI:

```bash
duckdb taxi_rides_ny.duckdb
```

### ❓ Question 1 – dbt Lineage

> If you run `dbt run --select int_trips_unioned`, what models will be built?

**Reasoning:**

- The `--select` flag without any operators (`+`) includes only the specified model.
- It does **not** automatically include upstream dependencies (like `stg_green_tripdata`, `stg_yellow_tripdata`) unless you use `--select +int_trips_unioned`.
- It also does **not** include downstream models (like `int_trips` or `fct_trips`) unless you use `--select int_trips_unioned+`.
- Therefore, only `int_trips_unioned` is built.

**Answer:** ✅ **int_trips_unioned only**

---

### ❓ Question 2 – dbt Test Behavior

> Given a generic test like this:
> ```yaml
> columns:
>   - name: payment_type
>     data_tests:
>       - accepted_values:
>           arguments:
>             values: [1, 2, 3, 4, 5]
>             quote: false
> ```
> Your model `fct_trips` runs successfully for months. A new value `6` appears in the source data. What happens when you run `dbt test --select fct_trips`?

**Reasoning:**

- dbt translates the test into a query similar to:
  ```sql
  SELECT * FROM fct_trips WHERE payment_type NOT IN (1,2,3,4,5)
  ```
- If any row has `payment_type = 6`, the query returns rows → the test **fails**.
- dbt will report a failure and exit with a **non-zero exit code**.

**Answer:** ✅ **dbt will fail the test, returning a non-zero exit code**

---

### ❓ Question 3 – Count records in `fct_monthly_zone_revenue`

```sql
SELECT COUNT(*) FROM prod.fct_monthly_zone_revenue;
```

**Result:** `14120`

**Explanation:**

- This table contains monthly aggregates per zone for each service type (Yellow/Green).
- The count reflects the number of combinations of zone, month, year, and service type.

**Answer:** ✅ **14,120**

---

### ❓ Question 4 – Best performing zone for Green taxis (2020)

```sql
SELECT
    zone,
    SUM(revenue_monthly_total_amount) AS total_revenue
FROM prod.fct_monthly_zone_revenue
WHERE service_type = 'Green'
  AND year = 2020
GROUP BY zone
ORDER BY total_revenue DESC
LIMIT 1;
```

**Result:** `East Harlem South`

**Explanation:**

- Filter for Green taxis only, year 2020.
- Sum monthly revenue per zone.
- Order descending and take top 1.

**Answer:** ✅ **East Harlem South**

---

### ❓ Question 5 – Green taxi trip counts in October 2019

```sql
SELECT
    SUM(total_monthly_trips)
FROM prod.fct_monthly_zone_revenue
WHERE service_type = 'Green'
  AND year = 2019
  AND month = 10;
```

**Result:** `384624`

**Explanation:**

- `total_monthly_trips` is already the sum of trips per zone per month.
- Summing over all zones gives the total trips for Green taxis in October 2019.

**Answer:** ✅ **384,624**

---

### ❓ Question 6 – Build a staging model for FHV data

#### Step 6.1 Verify raw FHV data exists

```sql
SELECT COUNT(*) FROM prod.fhv_tripdata;
```

If not loaded, ensure `load_data.py` ran the FHV part.

#### Step 6.2 Create the staging model

Create file `models/staging/stg_fhv_tripdata.sql`:

```sql
with source as (
    select * from {{ source('taxi_rides_ny', 'fhv_tripdata') }}
),

renamed as (
    select
        dispatching_base_num,
        pickup_datetime,
        dropoff_datetime,
        PUlocationID as pickup_location_id,
        DOlocationID as dropoff_location_id,
        SR_Flag as sr_flag
    from source
    where dispatching_base_num is not null
)

select * from renamed
```

**Explanation:**

- `{{ source(...) }}` refers to the raw table defined in `sources.yml` (not shown here, but present in the project).
- We rename columns to follow naming conventions (lowercase, underscores).
- Filter out rows where `dispatching_base_num IS NULL`, as required.

#### Step 6.3 Run the model

```bash
dbt run --select stg_fhv_tripdata --target prod
```

#### Step 6.4 Count the records

```sql
SELECT COUNT(*) FROM prod.stg_fhv_tripdata;
```

**Result:** `43244693`

**Explanation:**

- After filtering out NULL `dispatching_base_num`, the valid FHV 2019 records count is about 43.2 million.

**Answer:** ✅ **43,244,693**

---

## 🧠 Additional Knowledge Gained

### 📌 1. dbt Core Concepts

- **Models**: SQL files that define transformations. Each model is materialized as a view, table, or incremental table.
- **Sources**: Raw tables loaded outside dbt. Defined in `sources.yml` and referenced with `{{ source() }}`.
- **Ref**: Function to reference other models, enabling dbt to build the DAG automatically.
- **Tests**: Generic (built‑in) and singular (custom) tests to ensure data quality.
- **Seeds**: CSV files loaded into the warehouse as tables.
- **Packages**: Reusable libraries like `dbt_utils` that provide macros and tests.
- **Materializations**: Strategies for how models are built (`view`, `table`, `incremental`, `ephemeral`).

### 📌 2. ELT vs ETL

This project follows the **ELT** pattern:

- **Extract & Load**: Raw CSV files are loaded directly into DuckDB with minimal changes.
- **Transform**: All business logic, cleaning, and aggregation happen inside the warehouse using dbt.

Advantages of ELT:
- Leverages the power of the data warehouse for heavy transformations.
- Easier to audit and debug because raw data is always available.
- Scales better with cloud warehouses.

### 📌 3. Medallion Architecture (Bronze‑Silver‑Gold)

We implemented a simplified medallion architecture:

- **Bronze (Raw)**: `prod.yellow_tripdata`, `prod.green_tripdata`, `prod.fhv_tripdata` – unchanged source data.
- **Silver (Staging)**: `stg_*` models – cleaned, typed, and renamed; still at grain of original records.
- **Gold (Mart)**: `fct_trips`, `dim_zones`, `fct_monthly_zone_revenue` – aggregated, business‑ready tables.

This layered approach improves maintainability and reusability.

### 📌 4. dbt Testing for Data Quality

- **Generic tests**: `unique`, `not_null`, `accepted_values`, `relationships` (foreign key).
- **Singular tests**: Custom SQL assertions.
- **Outcome**: Tests act as documentation and prevent bad data from flowing into reports.
- In Question 2, the `accepted_values` test failed because a new, unexpected value appeared – this is exactly what tests are for.

### 📌 5. Incremental Models and Performance

- For large fact tables, incremental materialization can be used to only process new data.
- In this project, some models may be defined as `incremental` (e.g., `fct_trips`). Understanding when to use incremental vs. full refresh is crucial for production pipelines.

### 📌 6. Managing Environments (dev vs prod)

- We used two targets (`dev`, `prod`) in `profiles.yml` with separate schemas.
- Running with `--target prod` ensures we build the production models without affecting development work.
- This separation is a best practice for team collaboration.

### 📌 7. Optimization for Local / Resource‑Constrained Environments

- `memory_limit` in DuckDB prevents OOM errors.
- `preserve_insertion_order: false` speeds up aggregations.
- `threads: 1` avoids resource contention.
- Using `read_csv_auto` simplifies loading but may be slower; for production, consider partitioning or using Parquet.

### 📌 8. dbt Lineage and Documentation

- dbt automatically generates documentation and a DAG.
- The lineage graph helps understand dependencies and impact analysis.
- We can serve documentation with `dbt docs generate` and `dbt docs serve`.

### 📌 9. Packages and Macros

- `dbt_utils` provides useful macros like `date_spine`, `surrogate_key`, `union_relations`, etc.
- Using packages reduces boilerplate code and enforces consistency.

### 📌 10. Working with Large Datasets (Over 100 Million Rows)

- Even though we used a local DuckDB, the dataset exceeded 2.6 GB and ~115 million rows (Yellow + Green + FHV).
- We had to be mindful of memory limits and query performance.
- This simulates real‑world challenges of processing big data on limited hardware.

---

## 📊 Summary of Answers

| Question | Answer                              | Notes                                      |
| -------- | ----------------------------------- | ------------------------------------------ |
| Q1       | int_trips_unioned only              | No `+` operator means only that model      |
| Q2       | dbt fails with non-zero exit code   | Test catches unexpected value `6`          |
| Q3       | 14,120                              | Count from `fct_monthly_zone_revenue`      |
| Q4       | East Harlem South                   | Highest revenue Green taxi in 2020         |
| Q5       | 384,624                             | Total trips Green taxi, Oct 2019           |
| Q6       | 43,244,693                          | Staging FHV count after NULL filter        |

---

## 🏁 Conclusion

This homework provided a hands‑on experience with a complete ELT pipeline using dbt and DuckDB. We not only answered the specific questions but also learned:

- How to set up a dbt project from scratch.
- How to load raw data into a warehouse.
- How to build staging, intermediate, and fact models.
- How to test data quality.
- How to query and analyze the results.

The knowledge gained here forms the foundation for working as an Analytics Engineer in a modern data stack.

---

## 📎 Appendix

- **GitHub repository** (if applicable)
- **Full `load_data.py`** – see above
- **Full `profiles.yml`** – see above
- **Link to dbt documentation**: [https://docs.getdbt.com/](https://docs.getdbt.com/)
- **DuckDB documentation**: [https://duckdb.org/docs/](https://duckdb.org/docs/)

---

**Author:** Fathurrahman Hernanda khasan  
**Date:** February 2026  
**Course:** Data Engineering Zoomcamp (DataTalks.Club)