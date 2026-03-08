# scripts/q6_least_zone.py
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("hw6_q6") \
    .master("local[*]") \
    .getOrCreate()

trips = spark.read.parquet("data/yellow_tripdata_2025-11.parquet")
zones = spark.read.option("header","true").csv("data/taxi_zone_lookup.csv")

# cast LocationID
zones = zones.withColumn("LocationID", F.col("LocationID").cast("int"))
trips = trips.withColumn("PULocationID", F.col("PULocationID").cast("int"))

trips.createOrReplaceTempView("trips")
zones.createOrReplaceTempView("zones")

res = spark.sql("""
    SELECT z.Zone, COUNT(1) as trips
    FROM trips t
    JOIN zones z ON t.PULocationID = z.LocationID
    GROUP BY z.Zone
    ORDER BY trips ASC
    LIMIT 5
""")

res.show(truncate=False)
print("Q6 — least frequent zone (top 1 shown above).")

spark.stop()