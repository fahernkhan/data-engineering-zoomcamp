import pyarrow.dataset as ds
import pyarrow.compute as pc

DATA_DIR = "data/yellow_2024_parquet"

dataset = ds.dataset(DATA_DIR, format="parquet")

zero_fare_count = 0

for batch in dataset.to_batches(columns=["fare_amount"]):
    mask = pc.equal(batch.column("fare_amount"), 0)
    zero_fare_count += pc.sum(mask.cast("int64")).as_py()

print(f"Records with fare_amount = 0: {zero_fare_count}")
