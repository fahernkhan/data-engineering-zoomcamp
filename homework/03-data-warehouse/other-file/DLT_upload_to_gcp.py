# %% [markdown]
# **Please set up your credentials JSON as GCP_CREDENTIALS secrets**

# %%
import os
from google.colab import userdata

os.environ["DESTINATION__CREDENTIALS"] = userdata.get("GCP_CREDENTIALS")
os.environ["BUCKET_URL"] = "gs://your_bucket_url"

# %%
# Install for production
%%capture
!pip install dlt[bigquery, gs]

# %%
# Install for testing
%%capture
!pip install dlt[duckdb]

# %%
import dlt
import requests
import pandas as pd
from dlt.destinations import filesystem
from io import BytesIO

# %% [markdown]
# Ingesting parquet files to GCS.

# %%
# Define a dlt source to download and process Parquet files as resources
@dlt.source(name="rides")
def download_parquet():
    prefix = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata"
    for month in range(1, 7):
        file_name = f"yellow_tripdata_2024-0{month}.parquet"
        url = f"{prefix}_2024-0{month}.parquet"
        response = requests.get(url)

        df = pd.read_parquet(BytesIO(response.content))

        # Return the dataframe as a dlt resource for ingestion
        yield dlt.resource(df, name=file_name)


# Initialize the pipeline
pipeline = dlt.pipeline(
    pipeline_name="rides_pipeline",
    destination=filesystem(layout="{schema_name}/{table_name}.{ext}"),
    dataset_name="rides_dataset",
)

# Run the pipeline to load Parquet data into DuckDB
load_info = pipeline.run(download_parquet(), loader_file_format="parquet")

# Print the results
print(load_info)


# %% [markdown]
# Ingesting data to Database

# %%
# Define a dlt resource to download and process Parquet files as single table
@dlt.resource(name="rides", write_disposition="replace")
def download_parquet():
    prefix = 'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata'

    for month in range(1, 7):
        url = f"{prefix}_2024-0{month}.parquet"
        response = requests.get(url)

        df = pd.read_parquet(BytesIO(response.content))

        yield df


# Initialize the pipeline
pipeline = dlt.pipeline(
    pipeline_name="rides_pipeline",
    destination="duckdb",  # Use DuckDB for testing
    # destination="bigquery",  # Use BigQuery for production
    dataset_name="rides_dataset",
)

# Run the pipeline to load Parquet data into DuckDB
info = pipeline.run(download_parquet)

# Print the results
print(info)


# %%
import duckdb

conn = duckdb.connect(f"{pipeline.pipeline_name}.duckdb")

# Set search path to the dataset
conn.sql(f"SET search_path = '{pipeline.dataset_name}'")

# Describe the dataset to see loaded tables
res = conn.sql("DESCRIBE").df()
print(res)

# %%
# provide a resource name to query a table of that name
with pipeline.sql_client() as client:
    with client.execute_query(f"SELECT count(1) FROM rides") as cursor:
        data = cursor.df()
print(data)


