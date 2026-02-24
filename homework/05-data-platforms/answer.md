# 🚀 Module 5 Homework: End-to-End NYC Taxi Pipeline with Bruin

Welcome! This guide will walk you through building a complete data pipeline for NYC taxi data using Bruin. You'll learn by doing, and at the end you'll have the answers to all homework questions, backed by official documentation.

We'll use **DuckDB** as our local warehouse, but the same principles apply to BigQuery, Snowflake, etc.

---

## 📋 Prerequisites

- Terminal with `curl`, `git`
- Code editor (VS Code recommended with [Bruin extension](https://getbruin.com/docs/editors/vscode))
- Python 3.x (optional, only if using Python assets)

---

## 🔧 Step 1: Install Bruin CLI

Open your terminal and run:

```bash
curl -LsSf https://getbruin.com/install/cli | sh
# restart your shell or source profile
source ~/.bashrc  # or ~/.zshrc
bruin --version
```

*📚 [Official Installation Docs](https://getbruin.com/docs/getting-started/installation)*

---

## 🏗 Step 2: Initialize Project from Zoomcamp Template

The template provides a ready‑made structure with placeholders. Run:

```bash
bruin init zoomcamp my-taxi-pipeline
cd my-taxi-pipeline
```

Now list the contents – you'll see:

```
my-taxi-pipeline/
├── .bruin.yml          # Environment & connection config
├── pipeline.yml         # Pipeline definition (schedule, variables)
└── assets/              # Your SQL, Python, and ingestion YAML files
    ├── ingestion/
    ├── staging/
    └── reports/
```

> **✅ Question 1:** The required files/directories are **`.bruin.yml` and `pipeline.yml`** – assets can be organized anywhere (typically under `assets/`).  
> *📚 [Project Structure Docs](https://getbruin.com/docs/projects)*

---

## 🔌 Step 3: Configure DuckDB Connection

Edit `.bruin.yml` to set up a local DuckDB database:

```yaml
default_environment: default

environments:
  default:
    connections:
      duckdb:
        - name: "duckdb"
          path: "nyc_taxi.duckdb"
```

Save the file. This tells Bruin where to store data.

*📚 [Connections Documentation](https://getbruin.com/docs/connections/duckdb)*

---

## 📝 Step 4: Define Pipeline Variables

Open `pipeline.yml` and add a variable for taxi types. This allows us to filter which taxi data we process (e.g., only yellow taxis).

```yaml
name: nyc_taxi_pipeline
default_connections:
  duckdb: duckdb

variables:
  taxi_types:
    type: array
    items:
      type: string
    default: ["yellow", "green"]
```

*📚 [Variables Documentation](https://getbruin.com/docs/variables)*

---

## 🧱 Step 5: Create a Staging Asset with Incremental Logic

Inside `assets/staging/`, create a file `stg_trips.sql`. This asset will transform raw taxi trips. The magic is in the **materialization** section – we use `time_interval` to process one month at a time.

```sql
/* @bruin
name: staging.stg_trips
type: duckdb.sql
materialization:
  type: table
  strategy: time_interval      -- <-- Correct strategy
  incremental_key: pickup_datetime
  time_granularity: month
depends:
  - ingestion.trips_raw        -- (Assumes you have an ingestion asset)
columns:
  - name: pickup_datetime
    checks:
      - name: not_null         -- <-- Quality check for Question 5
*/

SELECT
  vendor_id,
  pickup_datetime,
  dropoff_datetime,
  passenger_count,
  trip_distance,
  fare_amount,
  -- Optionally use the taxi_types variable (via Jinja) if you have a taxi_type column
FROM ingestion.trips_raw
WHERE pickup_datetime BETWEEN '{{ start_date }}' AND '{{ end_date }}';
```

> **✅ Question 2:** The best incremental strategy for monthly processing is **`time_interval`** (deletes and inserts data for the interval).  
> *📚 [Materialization Docs](https://getbruin.com/docs/materialization)*

> **✅ Question 5:** To ensure `pickup_datetime` never has NULL values, add the quality check **`name: not_null`**.  
> *📚 [Data Quality Docs](https://getbruin.com/docs/data-quality)*

---

## 🧪 Step 6: Validate Your Pipeline

Before running, always validate:

```bash
bruin validate
```

This checks YAML syntax, dependencies, and connections.

*📚 [Validate Command Docs](https://getbruin.com/docs/commands/validate)*

---

## 🏃 Step 7: First Run – Full Refresh

Since this is your first run on an empty database, use `--full-refresh` to create all tables from scratch:

```bash
bruin run --full-refresh
```

> **✅ Question 7:** The flag to ensure tables are created from scratch on a new database is **`--full-refresh`**.  
> *📚 [Run Command Docs](https://getbruin.com/docs/commands/run)*

---

## 🎯 Step 8: Override Variables at Runtime

Now run the pipeline but only for yellow taxis (overriding the default array variable). Pay attention to the JSON syntax:

```bash
bruin run --var 'taxi_types=["yellow"]'
```

> **✅ Question 3:** The correct command to override an array variable is **`bruin run --var 'taxi_types=["yellow"]'`**.  
> *📚 [Run Command – Variables](https://getbruin.com/docs/commands/run#overriding-variables)*

---

## 🔀 Step 9: Run a Specific Asset and Its Downstream Dependencies

Suppose you modified `ingestion/trips.py` and want to run it plus everything that depends on it. Use the `--select` flag with `+`:

```bash
bruin run --select ingestion.trips+
```

The `+` means “this asset and all downstream assets”.

> **✅ Question 4:** The command is **`bruin run --select ingestion.trips+`**.  
> *📚 [Run Command – Selection](https://getbruin.com/docs/commands/run#selecting-assets)*

---

## 🔗 Step 10: Visualize Lineage

To see the dependency graph (lineage) of your assets, run:

```bash
bruin lineage
```

It will output a visual representation – helpful for documentation and debugging.

> **✅ Question 6:** The command to visualize dependencies is **`bruin lineage`**.  
> *📚 [Lineage Command Docs](https://getbruin.com/docs/commands/lineage)*

---

## 📚 Summary Table of Answers

| Question | Answer |
|----------|--------|
| 1 – Pipeline structure | `.bruin.yml` and `pipeline.yml` (assets can be anywhere) |
| 2 – Materialization for monthly data | `time_interval` |
| 3 – Override array variable | `bruin run --var 'taxi_types=["yellow"]'` |
| 4 – Run asset + downstream | `bruin run --select ingestion.trips+` |
| 5 – Quality check for no NULLs | `name: not_null` |
| 6 – Visualize dependencies | `bruin lineage` |
| 7 – First‑time run flag | `--full-refresh` |

---

## 💡 Lesson Learned

By following this guide, you’ve practiced the core concepts of a modern data platform:

- **Declarative configuration** with `.bruin.yml` and `pipeline.yml`
- **Incremental processing** using `time_interval` – essential for large datasets
- **Parameterization** with variables to make pipelines flexible
- **Data quality as code** – built‑in checks that block bad data
- **DAG awareness** – running only what’s needed with `--select`
- **Observability** – lineage to understand data flow

These are the building blocks of reliable, scalable data engineering.

Happy learning! 🚀