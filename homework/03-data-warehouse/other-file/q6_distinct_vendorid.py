import pyarrow.dataset as ds
import pyarrow.compute as pc
import pyarrow as pa
from datetime import datetime

DATA_DIR = "data/yellow_2024_parquet"

dataset = ds.dataset(DATA_DIR, format="parquet")

start = datetime(2024, 3, 1)
end = datetime(2024, 3, 15, 23, 59, 59)

vendor_ids = set()

for batch in dataset.to_batches(
    columns=["VendorID", "tpep_dropoff_datetime"]
):
    mask = pc.and_(
        pc.greater_equal(batch.column("tpep_dropoff_datetime"), pa.scalar(start)),
        pc.less_equal(batch.column("tpep_dropoff_datetime"), pa.scalar(end))
    )

    filtered = batch.filter(mask)
    vendor_ids.update(filtered.column("VendorID").to_pylist())

print(f"Distinct VendorID (2024-03-01 to 2024-03-15): {sorted(vendor_ids)}")
print(f"Count: {len(vendor_ids)}")
