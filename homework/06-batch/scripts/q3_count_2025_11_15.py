# scripts/q3_count_2025_11_15.py
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("hw6_q3") \
    .master("local[*]") \
    .getOrCreate()

df = spark.read.parquet("data/yellow_tripdata_2025-11.parquet")

# deteksi nama kolom pickup
pickup_col = next((c for c in df.columns if "pickup" in c.lower()), None)
if pickup_col is None:
    raise SystemExit("pickup column not found")

cnt = df.withColumn("pickup_date", F.to_date(F.col(pickup_col))) \
        .filter(F.col("pickup_date") == F.lit("2025-11-15")) \
        .count()

print("Q3 — Trips started on 2025-11-15:", cnt)
spark.stop()