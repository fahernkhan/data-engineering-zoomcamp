import pyarrow.dataset as ds

DATA_DIR = "data/yellow_2024_parquet"

dataset = ds.dataset(DATA_DIR, format="parquet")

table = dataset.to_table(columns=["PULocationID"])
distinct_values = table.column("PULocationID").unique()

print(f"Distinct PULocationID count: {len(distinct_values)}")
