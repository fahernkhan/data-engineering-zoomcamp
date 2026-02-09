import os
import pyarrow.parquet as pq

DATA_DIR = "data/yellow_2024_parquet"

total_rows = 0

for file in sorted(os.listdir(DATA_DIR)):
    if file.endswith(".parquet"):
        path = os.path.join(DATA_DIR, file)
        parquet_file = pq.ParquetFile(path)
        rows = parquet_file.metadata.num_rows
        total_rows += rows
        print(f"{file}: {rows:,}")

print("\n==============================")
print(f"TOTAL ROWS (Jan–Jun 2024): {total_rows:,}")
print("==============================")
