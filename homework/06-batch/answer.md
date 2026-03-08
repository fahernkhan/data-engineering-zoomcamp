# 🚀 Homework 6: Batch Processing with Spark  
## Data Engineering Zoomcamp 2026  

---

## 📖 Overview  

This homework focuses on **Apache Spark** and **PySpark** for batch processing. We use the **Yellow Taxi Trip Records** for November 2025 (Parquet format) and the **Taxi Zone Lookup** CSV. The goal is to answer six questions that test basic Spark operations: reading data, repartitioning, filtering, aggregations, joins, and understanding the Spark UI.  

All steps are implemented using **PySpark** with a **local Spark session**, managed via **`uv`** for dependency isolation.  

---

## ⚙️ Environment Setup  

We use **`uv`** (a fast Python package installer) to create a virtual environment and install PySpark.  

### 1. Install `uv` (if not already)  

```bash
pip install uv
```

### 2. Create project directory and initialize  

```bash
mkdir -p ~/Documents/data_engineer/data-engineering-zoomcamp/homework/06-batch
cd ~/Documents/data_engineer/data-engineering-zoomcamp/homework/06-batch
uv init
```

### 3. Add PySpark  

```bash
uv add pyspark
```

### 4. Download the data  

```bash
wget https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-11.parquet
wget https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```

### 5. Organise files  

```bash
mkdir -p data scripts
mv yellow_tripdata_2025-11.parquet data/
mv taxi_zone_lookup.csv data/
```

### 6. Final project structure  

```
06-batch/
├─ data/
│  ├─ yellow_tripdata_2025-11.parquet
│  └─ taxi_zone_lookup.csv
├─ scripts/
│  ├─ q1_version.py
│  ├─ q2_repartition.py
│  ├─ q3_count_2025_11_15.py
│  ├─ q4_longest_trip.py
│  ├─ q5_spark_ui.md
│  └─ q6_least_zone.py
├─ run_all.sh
├─ .gitignore
├─ pyproject.toml
└─ uv.lock
```

---

## 📝 Question‑by‑Question Walkthrough  

### **Question 1: Install Spark and PySpark**  

**Task:** Create a local Spark session and print `spark.version`.  

**Solution (`scripts/q1_version.py`):**  

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("hw6_q1") \
    .master("local[*]") \
    .getOrCreate()

print("Q1 — spark.version:", spark.version)
spark.stop()
```

**Run:**  

```bash
uv run python scripts/q1_version.py
```

**Output:**  

```
Q1 — spark.version: 4.1.1
```

**Answer:** **4.1.1**  

---

### **Question 2: Yellow November 2025 – Repartition to 4 and save as Parquet**  

**Task:** Read the Parquet file, repartition to 4 partitions, write back to Parquet, and compute the **average size** of the resulting files.  

**Solution (`scripts/q2_repartition.py`):**  

```python
from pyspark.sql import SparkSession
from pathlib import Path

def avg_parquet_size_mb(output_dir):
    p = Path(output_dir)
    sizes = [f.stat().st_size for f in p.iterdir() 
             if f.is_file() and (f.suffix == ".parquet" or f.name.startswith("part-"))]
    return (sum(sizes)/len(sizes))/(1024*1024) if sizes else 0.0

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
```

**Run:**  

```bash
uv run python scripts/q2_repartition.py
```

**Output:**  

```
Q2 — Average parquet file size (MB): 24.42 MB
```

**Insight:**  
The original file is ~68 MB. After `repartition(4)`, Spark writes 4 files of roughly equal size. Compression and metadata overhead bring the average to **~24 MB**, closest to **25 MB** among the options.  

**Answer:** **25 MB**  

---

### **Question 3: Count records on 15th November**  

**Task:** Count trips that started on **2025-11-15**.  

**Solution (`scripts/q3_count_2025_11_15.py`):**  

```python
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("hw6_q3") \
    .master("local[*]") \
    .getOrCreate()

df = spark.read.parquet("data/yellow_tripdata_2025-11.parquet")

pickup_col = next((c for c in df.columns if "pickup" in c.lower()), None)
if not pickup_col:
    raise SystemExit("pickup column not found")

cnt = df.withColumn("pickup_date", F.to_date(F.col(pickup_col))) \
        .filter(F.col("pickup_date") == "2025-11-15") \
        .count()

print("Q3 — Trips started on 2025-11-15:", cnt)
spark.stop()
```

**Run:**  

```bash
uv run python scripts/q3_count_2025_11_15.py
```

**Output:**  

```
Q3 — Trips started on 2025-11-15: 162604
```

**Answer:** **162,604**  

---

### **Question 4: Longest trip in hours**  

**Task:** Find the maximum trip duration (in hours).  

**Important:** Spark 4.x uses `timestamp_ntz` which cannot be directly cast to `long`. We use `unix_timestamp()` to convert to seconds.  

**Solution (`scripts/q4_longest_trip.py`):**  

```python
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("hw6_q4") \
    .master("local[*]") \
    .getOrCreate()

df = spark.read.parquet("data/yellow_tripdata_2025-11.parquet")

pickup_col = next((c for c in df.columns if "pickup" in c.lower()), None)
dropoff_col = next((c for c in df.columns if "dropoff" in c.lower()), None)
if not pickup_col or not dropoff_col:
    raise SystemExit("pickup/dropoff columns not found")

duration_sec = F.unix_timestamp(F.col(dropoff_col)) - F.unix_timestamp(F.col(pickup_col))
df_dur = df.withColumn("duration_hours", duration_sec / 3600.0)
max_dur = df_dur.agg(F.max("duration_hours")).collect()[0][0]

print("Q4 — Longest trip (hours):", max_dur)
spark.stop()
```

**Run:**  

```bash
uv run python scripts/q4_longest_trip.py
```

**Output:**  

```
Q4 — Longest trip (hours): 90.64666666666666
```

**Answer:** **90.6**  

---

### **Question 5: Spark UI port**  

**Task:** Identify the default local port of Spark’s web UI.  

**Explanation:**  
Spark’s application dashboard runs on **port 4040** by default. You can access it at `http://localhost:4040` while a Spark job is running.  

**Solution:** We created a simple markdown file `scripts/q5_spark_ui.md` with this information.  

**Answer:** **4040**  

---

### **Question 6: Least frequent pickup location zone**  

**Task:** Join the trip data with the taxi zone lookup and find the zone with the fewest pickups.  

**Solution (`scripts/q6_least_zone.py`):**  

```python
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("hw6_q6") \
    .master("local[*]") \
    .getOrCreate()

trips = spark.read.parquet("data/yellow_tripdata_2025-11.parquet")
zones = spark.read.option("header","true").csv("data/taxi_zone_lookup.csv")

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
```

**Run:**  

```bash
uv run python scripts/q6_least_zone.py
```

**Output:**  

```
+---------------------------------------------+-----+
|Zone                                         |trips|
+---------------------------------------------+-----+
|Governor's Island/Ellis Island/Liberty Island|1    |
|Eltingville/Annadale/Prince's Bay            |1    |
|Arden Heights                                |1    |
|Port Richmond                                |3    |
|Rikers Island                                |4    |
+---------------------------------------------+-----+

Q6 — least frequent zone (top 1 shown above).
```

**Note:** Three zones have exactly **1 pickup**. The SQL `ORDER BY trips ASC` returns them in alphabetical order; the first one is **Governor's Island/Ellis Island/Liberty Island**. The question states: *“If multiple answers are correct, select any”* – so this is valid.  

**Answer:** **Governor's Island/Ellis Island/Liberty Island**  

---

## 🧠 Lessons Learned & Key Insights  

### 1. **Spark 4.x and `timestamp_ntz`**  
   - In Spark 4, timestamp columns without time zone are stored as `timestamp_ntz`.  
   - Direct casting to `long` (`col.cast('long')`) fails – use `unix_timestamp()` instead.  
   - This is critical for time-difference calculations.  

### 2. **Repartitioning and File Sizes**  
   - `repartition(n)` triggers a full shuffle and creates **exactly n** files (one per partition).  
   - The average file size is approximately `original_size / n` plus some overhead due to Parquet metadata and compression.  
   - Knowing this helps estimate storage and optimize Spark jobs.  

### 3. **Spark UI**  
   - The UI is invaluable for debugging and performance tuning.  
   - Default port **4040**; if multiple apps run, ports increment (4041, 4042, …).  
   - You can view DAG, stage details, task timelines, and executor metrics.  

### 4. **DataFrames vs SQL**  
   - Both APIs are powerful. SQL can be more readable for multi‑table joins; DataFrames offer type safety and programmability.  
   - Registering a temp view allows seamless mixing of both styles.  

### 5. **Handling Column Names**  
   - Yellow taxi data uses column names like `tpep_pickup_datetime`; our scripts dynamically detect columns containing “pickup” or “dropoff” – robust against minor naming variations.  

### 6. **Join Performance**  
   - Joining a large fact table (trips) with a small dimension (zones) is efficient; Spark broadcasts small tables automatically if `spark.sql.autoBroadcastJoinThreshold` is not exceeded.  

### 7. **Using `uv` for Dependency Management**  
   - `uv` is extremely fast and keeps environments clean.  
   - The `uv run` command automatically uses the virtual environment, avoiding global package conflicts.  

### 8. **Script Modularity**  
   - Splitting each question into a separate script makes debugging easier and allows running them independently.  
   - The `run_all.sh` script demonstrates how to orchestrate them sequentially.  

---

## 📁 Repository & Automation  

- **`run_all.sh`** – executes all scripts in order and prints answers.  
  ```bash
  chmod +x run_all.sh
  ./run_all.sh
  ```

- **`.gitignore`** – excludes virtual environment, data files, and temporary Spark directories.  

- **`README.md`** – (this document) serves as both homework submission and learning diary.  

---

## 🧪 Final Answers for Submission  

| Question | Answer                                      |
|----------|---------------------------------------------|
| Q1       | 4.1.1                                       |
| Q2       | 25 MB                                       |
| Q3       | 162,604                                     |
| Q4       | 90.6                                        |
| Q5       | 4040                                        |
| Q6       | Governor's Island/Ellis Island/Liberty Island |

---

## 🌐 Learning in Public  

Sharing your work helps solidify knowledge and contributes to the community. Here’s a sample LinkedIn post:

> 🚀 Week 6 of Data Engineering Zoomcamp by @DataTalksClub complete!  
> Just finished Module 6 – Batch Processing with Spark. Learned how to:  
> ✅ Set up PySpark with `uv`  
> ✅ Read and repartition Parquet files  
> ✅ Calculate durations using `unix_timestamp` (Spark 4 fix)  
> ✅ Use Spark UI for monitoring  
> ✅ Join with zone lookup to find least frequent pickup zone  
>  
> Processing millions of taxi trips with Spark – distributed computing is powerful! 💪  
>  
> Here's my solution: [link to your repo]  
>  
> Following along with this amazing free course – who else is learning data engineering?  
>  
> You can sign up here: https://github.com/DataTalksClub/data-engineering-zoomcamp/  

---

## 📚 References  

- [Data Engineering Zoomcamp GitHub](https://github.com/DataTalksClub/data-engineering-zoomcamp)  
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)  
- [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)  

---
## uv run python -c "import sys; print(sys.executable)" 

**Happy Learning!** 🎉