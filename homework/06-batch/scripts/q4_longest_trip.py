# scripts/q4_longest_trip.py
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("hw6_q4") \
    .master("local[*]") \
    .getOrCreate()

df = spark.read.parquet("data/yellow_tripdata_2025-11.parquet")

pickup_col = next((c for c in df.columns if "pickup" in c.lower()), None)
dropoff_col = next((c for c in df.columns if "dropoff" in c.lower()), None)
if pickup_col is None or dropoff_col is None:
    raise SystemExit("pickup/dropoff columns not found")

# gunakan unix_timestamp untuk kompatibilitas timestamp_ntz
duration_sec = F.unix_timestamp(F.col(dropoff_col)) - F.unix_timestamp(F.col(pickup_col))
df_dur = df.withColumn("duration_hours", duration_sec / 3600.0)
max_dur = df_dur.agg(F.max("duration_hours")).collect()[0][0]

print("Q4 — Longest trip (hours):", max_dur)
spark.stop()