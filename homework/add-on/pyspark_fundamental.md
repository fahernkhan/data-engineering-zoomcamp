# Spark / PySpark Playbook — **Lengkap & Production-Ready**

Versi praktis untuk Data Engineer: pola, tuning, checklist, contoh kode, deployment, monitoring, testing, dan anti-pattern. Ditulis ringkas tapi lengkap supaya bisa langsung diterapkan.

> Bahasa: **Bahasa Indonesia** (sesuai preferensimu).
> Fokus: batch (Mongo → GCS → BigQuery), JDBC, CDC, streaming (Kafka), join-heavy jobs, skew, dan production ops.

---

# 1. Mental model & prinsip utama

* **Spark = builder DAG (lazy)** — hanya dieksekusi saat Action (count/write/collect) dipanggil.
* **Push computation to source** (pushdown) — filter/limit di source selalu prioritas.
* **Minimise shuffle** — shuffle mahal: desain partition & join strategy agar minim.
* **Memory discipline** — cache/persist hanya saat perlu, selalu `unpersist()` setelah selesai.
* **Idempotency** — job harus aman di-re-run (staging → merge pattern).
* **Observability** — Spark UI + metrics + structured logs + alerts wajib.

---

# 2. Struktur repo rekomendasi (production)

```
project/
├─ infra/                  # terraform/k8s templates
├─ dags/                   # orchestration (Airflow, Prefect)
├─ jobs/
│  ├─ mongo_to_bq/
│  │  ├─ main.py
│  │  ├─ utils.py
│  │  └─ jars/
│  └─ jdbc_to_lake/
├─ tests/
│  ├─ unit/
│  └─ integration/
├─ docker/
│  └─ Dockerfile
├─ conf/
│  ├─ spark-defaults.conf
│  └─ logging.conf
├─ build/                  # build artifacts
└─ README.md
```

---

# 3. Production-ready SparkSession template (PySpark)

```python
from pyspark.sql import SparkSession

def build_spark(app_name, master=None, jars=None, confs=None):
    b = SparkSession.builder.appName(app_name)
    if master:
        b = b.master(master)
    if jars:
        b = b.config("spark.jars", ",".join(jars))
    base_confs = {
        # Adaptive + shuffle
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
        "spark.sql.adaptive.skewJoin.enabled": "true",
        "spark.sql.shuffle.partitions": "200",
        "spark.sql.autoBroadcastJoinThreshold": str(20 * 1024 * 1024),  # 20MB
        # parquet / timestamp
        "spark.sql.parquet.datetimeRebaseModeInWrite": "LEGACY",
        "spark.sql.parquet.outputTimestampType": "TIMESTAMP_MILLIS",
        # monitoring
        "spark.executor.logs.rolling.maxRetainedFiles": "5",
        "spark.executor.logs.rolling.strategy": "time",
    }
    if confs:
        base_confs.update(confs)
    for k, v in base_confs.items():
        b = b.config(k, v)
    return b.getOrCreate()
```

---

# 4. Core patterns & contoh (copy-paste ready)

## 4.1 Extract with pushdown (Mongo)

```python
pipeline = json.dumps([{"$match": {"dtupdate": {"$gte": {"$date": cutoff_iso}}}}])
df = (spark.read
      .format("com.mongodb.spark.sql.DefaultSource")
      .option("uri", uri)
      .option("database", db)
      .option("collection", coll)
      .option("pipeline", pipeline)
      .option("partitioner", "MongoSamplePartitioner")
      .option("sampleSize", "10000")
      .load())
```

## 4.2 Transform / column hygiene

```python
from pyspark.sql.functions import regexp_replace, col

# remove null bytes + standardize names
df = df
for c in df.schema.names:
    if df.schema[c].dataType.simpleString() == "string":
        df = df.withColumn(c, regexp_replace(col(c), "\u0000", ""))
# rename to snake_case -> implement util function
```

## 4.3 Materialize + dynamic partitioning pattern

```python
from pyspark import StorageLevel

df = df.transform(transform_df)
df = df.persist(StorageLevel.MEMORY_AND_DISK)
count = df.count()  # materialize
if count == 0: 
    df.unpersist(); return

num_partitions = max(8, int(count // 500_000))
spark.conf.set("spark.sql.shuffle.partitions", str(num_partitions))
df2 = df.repartition(num_partitions)
df.unpersist(blocking=False)  # release original cache
df2.write.mode("overwrite").parquet(gcs_path)
df2.unpersist()
```

## 4.4 Safe BigQuery load (staging)

* Write to GCS Parquet
* Load to BQ staging table (WRITE_TRUNCATE)
* dbt merge/insert into final table (delete+insert atau MERGE)

---

# 5. Partitioning — aturan praktis

* **Target file size**: 128–512 MB per parquet file.
* **Rows per partition**: 200K–1M rows (rule of thumb).
* **Set `spark.sql.shuffle.partitions`** sesuai `num_partitions`.
* **Avoid tiny files**: gunakan `coalesce()` atau `repartition()` sebelum write.

---

# 6. Persist / Cache / Unpersist — kapan & kenapa

* `persist()`/`cache()` = simpan hasil transform di memory/disk untuk reuse.
* **Gunakan kalau**: hasil dipakai lebih dari 1x (multiple actions, multiple downstream joins) atau sebelum expensive repartition/joins.
* **Risiko**: memakai memory besar → OOM.
* **Best practice**:

  1. `df = df.persist(StorageLevel.MEMORY_AND_DISK)`
  2. `df.count()` untuk materialize (opsional, agar DAG dipaksakan sekali)
  3. lakukan operasi berat (repartition, joins)
  4. `df.unpersist(blocking=False)` setelah selesai
* `unpersist()` penting supaya memory freed (sepenting itu di cluster multi-job).

---

# 7. Repartition vs Coalesce

* `repartition(n)` → full shuffle, buat distribusi data rata (mahal).
* `coalesce(n)` → tanpa shuffle (baik untuk mengurangi partisi).
* **Pattern**:

  * scale up before heavy joins: `repartition(num)` by key (jika join key diketahui)
  * right before write: `coalesce(n_files)` untuk mengurangi small files

---

# 8. Join strategies

* **Broadcast join** jika small dataset (hasil `spark.sparkContext.broadcast()` threshold).
* **SortMergeJoin** default untuk big joins; optim: set `spark.sql.autoBroadcastJoinThreshold` & ensure partitioning by join key.
* **Skew**: gunakan salting atau AQE skew join support (`spark.sql.adaptive.skewJoin.enabled=true`).

---

# 9. Skew mitigation teknik

1. **Salting**: tambahkan random bucket pada key di satu sisi, join on (key, salt).
2. **Split heavy keys**: detect heavy keys and handle separately.
3. **Broadcast heavy small lookup**.
4. **Adaptive Query Execution (AQE)**: aktifkan untuk mengurangi skew.

---

# 10. Monitoring & Observability

* **Spark UI** (lokal `http://localhost:4040`), cluster UI, Spark History Server.
* **Metrics**: expose metrics (JMX / Prometheus exporter) → dashboards (Grafana).
* **Logs**: structured JSON logs, per-job run_id, job_tag.
* **Alerting**: task failure rate, job duration > baseline, executor OOM, GC pressure.

---

# 11. Testing & CI

* **Unit test**: pytest + `pyspark.sql.SparkSession.builder.master("local[2]")` untuk unit tests.
* **Integration test**: run a small job against test Mongo / small parquet fixture.
* **Linting**: flake8 / black.
* **CI pipeline**:

  * Unit tests (fast)
  * Build image/artifact
  * Integration tests against staging infra
  * Deploy via CD

---

# 12. Packaging & Deployment

* **Local dev**: `spark-submit --master local[*] ...`
* **Cluster**:

  * YARN (on-prem, EMR/YARN)
  * Kubernetes (Spark on K8s)
  * Managed: Dataproc, EMR, GKE/Dataproc Serverless
* **Container**: build Docker with Python + Spark runtime (use lightweight images).
* **JAR / fat-jar**: untuk Scala/Java jobs use fat jar.
* **Config externalization**: semua secrets/config di Secret Manager / Vault, jangan hardcode.

---

# 13. Security

* Use service accounts with least privilege.
* GCS/BQ access: IAM roles (no wide permissions).
* Secrets: store in KMS/Secret Manager/Vault.
* Network: private VPC, peering, firewall rules.

---

# 14. Data Quality (DQ) & Observability integration

* Run Great Expectations / custom validators in pipeline (post-transform, pre-write).
* Store DQ results (metrics) into DQ table (period, dqi_id, good_percent, bad_list).
* If DQ fails: stop pipeline, raise alert & store report.

---

# 15. Common Configs (recommended baseline)

```
spark.driver.memory=4g
spark.executor.memory=8g
spark.executor.cores=2
spark.executor.instances=4
spark.sql.shuffle.partitions=200 (tweak per job)
spark.sql.adaptive.enabled=true
spark.sql.autoBroadcastJoinThreshold=20971520
spark.default.parallelism=auto (or num_executors * cores)
```

Tweak menurut cluster size & job profile.

---

# 16. Checklist sebelum produksi (pre-go-live)

* [ ] Filter & pushdown diterapkan
* [ ] No secret hardcoded
* [ ] Partitions & shuffle tuned
* [ ] Target parquet file size ok (128–512MB)
* [ ] Checkpoints (untuk streaming) valid
* [ ] Retries & idempotency (WRITE_TRUNCATE ke staging)
* [ ] Monitoring / alerting configured
* [ ] DQ rules run (GE or custom)
* [ ] Logs structured + run_id
* [ ] Spark UI access & history available

---

# 17. Troubleshooting cepat (FAQ singkat)

* **Job lambat** → lihat `df.explain("formatted")` → banyak `Exchange`? → shuffle heavy → increase partitions or optimize joins.
* **OOM** → kurangi cache, turunkan executor memory, increase executors, tambahkan spill to disk (MEMORY_AND_DISK).
* **Small files** → gunakan `repartition()` sebelum write → target file size.
* **Broadcast tidak terjadi** → cek `spark.sql.autoBroadcastJoinThreshold` dan ukuran tabel kecil.

---

# 18. Snippets berguna (cheat sheet)

**Check execution plan**

```python
df.explain(mode="formatted")
```

**Persist / materialize**

```python
df = df.persist(StorageLevel.MEMORY_AND_DISK)
row_count = df.count()  # materialize
# ... later
df.unpersist()
```

**Set shuffle partitions**

```python
spark.conf.set("spark.sql.shuffle.partitions", "32")
```

**Broadcast join**

```python
from pyspark.sql.functions import broadcast
big.join(broadcast(small), "id")
```

**Write parquet with partition columns**

```python
df.write.mode("overwrite").partitionBy("period").parquet(path)
```

---

# 19. Contoh end-to-end checklist (Mongo→GCS→BQ incremental)

1. Build pipeline with pushdown (7 days)
2. Extract with Mongo partitioner & sampleSize
3. Clean columns & types, convert NullType → string
4. Persist then count (materialize snapshot)
5. Calculate partitions; set `spark.sql.shuffle.partitions`
6. Repartition safely (by key if joining later)
7. Write to GCS as parquet (target file size)
8. Load to BQ staging via service account (WRITE_TRUNCATE)
9. Run dbt (MERGE into final)
10. Run DQ checks; store results & alert if fail

---

# 20. Penutup — rekomendasi final

* Untuk **stabil & cepat**: aktifkan AQE, gunakan pushdown, hitung snapshot saat reuse, atur shuffle partitions dinamis, dan jangan lupa `unpersist()`.
* Simpan pola ini sebagai template job, dan buat test + monitoring untuk setiap job.
* Kalau mau, aku bisa:

  * Generate **template job file** (ready to copy-paste) untuk Mongo→GCS→BQ termasuk DQ step.
  * Buat **CI pipeline example** (GitHub Actions) untuk testing & build.
  * Buat **Grafana dashboard template** untuk Spark metrics.

Mau aku buatkan salah satu (contoh job template / CI / dashboard) sekarang?
