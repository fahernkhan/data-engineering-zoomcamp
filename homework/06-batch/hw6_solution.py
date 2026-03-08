# hw6_solution.py
from pyspark.sql import SparkSession, functions as F
import os
import sys
from pathlib import Path

def human_mb(sz_bytes):
    return sz_bytes / (1024*1024)

def avg_parquet_size_mb(output_dir):
    p = Path(output_dir)
    if not p.exists():
        return None
    sizes = []
    for f in p.iterdir():
        if f.is_file() and f.suffix == ".parquet":
            sizes.append(f.stat().st_size)
    if not sizes:
        # also accept part-* files without .parquet extension
        for f in p.iterdir():
            if f.is_file() and f.name.startswith("part-"):
                sizes.append(f.stat().st_size)
    if not sizes:
        return 0.0
    return sum(sizes) / len(sizes) / (1024*1024)

def main():
    # 1) create spark session (local)
    spark = SparkSession.builder \
        .appName("zoomcamp_hw6_solution") \
        .master("local[*]") \
        .config("spark.sql.shuffle.partitions", "4") \
        .getOrCreate()

    print("Q1 — spark.version:", spark.version)
    print("Spark UI: check http://localhost:4040 while job runs (default port).")

    # 2) read parquet dataset
    path_parquet = "yellow_tripdata_2025-11.parquet"
    if not Path(path_parquet).exists():
        print(f"ERROR: dataset file {path_parquet} not found in cwd.", file=sys.stderr)
        spark.stop()
        sys.exit(2)

    print("\nReading parquet:", path_parquet)
    df = spark.read.parquet(path_parquet)
    print("Schema preview:")
    df.printSchema()
    print("Count preview (first 5 rows):")
    df.show(5, truncate=False)

    # normalize pickup / dropoff column names - supports both tpep_ and generic names
    cols = df.columns
    pickup_col = None
    dropoff_col = None
    for c in cols:
        lc = c.lower()
        if "pickup" in lc and ("tpep" in lc or "pickup_datetime" in lc or "pickup" in lc):
            pickup_col = c
        if "dropoff" in lc and ("tpep" in lc or "dropoff_datetime" in lc or "dropoff" in lc):
            dropoff_col = c

    if pickup_col is None or dropoff_col is None:
        print("ERROR: Could not find pickup/dropoff datetime columns.", file=sys.stderr)
        spark.stop()
        sys.exit(3)

    print(f"Using pickup column: {pickup_col}, dropoff column: {dropoff_col}")

    # 3) repartition to 4 and write parquet out
    out_dir = "yellow_2025_11_repart4"
    print(f"\nRepartitioning to 4 and writing parquet to {out_dir}/ ... (this may take a while)")
    df_repart = df.repartition(4)
    # write in overwrite mode
    df_repart.write.mode("overwrite").parquet(out_dir)

    # 4) compute average parquet file size (MB)
    avg_mb = avg_parquet_size_mb(out_dir)
    print(f"\nQ2 — Average parquet file size (MB): {avg_mb:.2f} MB")
    # you can choose closest answer accordingly

    # 5) Q3: how many trips started on 2025-11-15?
    df2 = df.withColumn("pickup_date", F.to_date(F.col(pickup_col)))
    cnt_15 = df2.filter(F.col("pickup_date") == F.lit("2025-11-15")).count()
    print(f"\nQ3 — Trips started on 2025-11-15: {cnt_15}")

    # 6) Q4: longest trip in hours
    duration_sec = (
        F.unix_timestamp(F.col(dropoff_col)) -
        F.unix_timestamp(F.col(pickup_col))
    )

    df_dur = df.withColumn("duration_hours", duration_sec / 3600)

    max_dur = df_dur.agg(F.max("duration_hours")).collect()[0][0]

    print(f"\nQ4 — Longest trip (hours): {max_dur}")

    # 7) Q5: Spark UI port
    print("\nQ5 — Spark UI default port is 4040 (open http://localhost:4040 when job runs).")

    # 8) Q6: least frequent pickup zone (join with taxi_zone_lookup.csv)
    zones_csv = "taxi_zone_lookup.csv"
    if not Path(zones_csv).exists():
        print(f"WARNING: {zones_csv} not found, skipping Q6 (download file first).", file=sys.stderr)
    else:
        zones = spark.read.option("header", "true").csv(zones_csv)
        # ensure types
        zones = zones.withColumn("LocationID", F.col("LocationID").cast("int"))
        zones.createOrReplaceTempView("zones")
        df.createOrReplaceTempView("trips")
        q = """
        SELECT z.Zone, COUNT(1) AS trips
        FROM trips t
        JOIN zones z ON CAST(t.PULocationID AS INT) = z.LocationID
        GROUP BY z.Zone
        ORDER BY trips ASC
        LIMIT 1
        """
        least = spark.sql(q).collect()
        if least:
            print(f"\nQ6 — Least frequent pickup zone: {least[0]['Zone']}  (trips={least[0]['trips']})")
        else:
            print("\nQ6 — Could not compute least frequent pickup zone (no results).")

    spark.stop()

if __name__ == "__main__":
    main()