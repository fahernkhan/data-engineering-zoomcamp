import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pyarrow as pa

INPUT_DIR = "data/yellow_2024_parquet"
OUTPUT_FILE = "data/yellow_2024_jan_jun.parquet"

dataset = ds.dataset(INPUT_DIR, format="parquet")

writer = None

for batch in dataset.to_batches():
    table = pa.Table.from_batches([batch])

    if writer is None:
        writer = pq.ParquetWriter(
            OUTPUT_FILE,
            table.schema,
            compression="snappy"
        )

    writer.write_table(table)

if writer:
    writer.close()

print(f"✅ Merged parquet written to: {OUTPUT_FILE}")
