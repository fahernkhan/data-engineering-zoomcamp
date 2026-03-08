# scripts/q2_repartition.py
from pyspark.sql import SparkSession
from pathlib import Path
import os

def avg_parquet_size_mb(output_dir):
    p = Path(output_dir)
    sizes = []
    for f in p.iterdir():
        if f.is_file() and (f.suffix == ".parquet" or f.name.startswith("part-")):
            sizes.append(f.stat().st_size)
    if not sizes:
        return 0.0
    return sum(sizes)/len(sizes) / (1024*1024)

spark = SparkSession.builder \
    .appName("hw6_q2") \
    .master("local[*]") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

in_path = "data/yellow_tripdata_2025-11.parquet"
out_dir = "data/yellow_2025_11_repart4"

df = spark.read.parquet(in_path)
df_repart = df.repartition(4)
df_repart.write.mode("overwrite").parquet(out_dir)

avg_mb = avg_parquet_size_mb(out_dir)
print(f"Q2 — Average parquet file size (MB): {avg_mb:.2f} MB")

spark.stop()