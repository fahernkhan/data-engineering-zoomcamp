Bagus — aku susun panduan **dari 0 → siap develop & deploy Spark** yang praktis, fokus ke *setup*, *flow* (batch & streaming), integrasi connector (GCS / Mongo), testing, dan best practices. Langsung ke poin, step-by-step — pakai contoh kode kecil supaya bisa langsung dicoba.

# 1) Gambaran singkat flow pengembangan Spark

1. **Setup environment** (Java, Spark, Python/venv, driver JARs)
2. **Buat project skeleton** (src, tests, configs)
3. **Tulis code**: pisahkan `extract()`, `transform()`, `load()` → mudah diuji
4. **Test lokal** (unit + integration dengan Spark local)
5. **Package** (wheel / fat-jar / Docker) + dependency JARs untuk connector
6. **Deploy**: spark-submit (cluster / Dataproc / EMR) atau run container di cluster
7. **Monitoring & retries** (logs, alert, idempotency)

# 2) Prerequisites & install (local dev)

* **Java**: JDK 11 atau 17 (Spark 3.x umum pakai Java 11) — pastikan `JAVA_HOME` ter-set.
* **Python**: 3.8–3.11 (pakai venv).
* **Spark**: download Spark binary (prebuilt for Hadoop3) atau gunakan `pip install pyspark` untuk dev (tapi connector JAR tetap perlu).
* **Win (Windows)**: pasang `winutils.exe` jika perlu; set `HADOOP_HOME` ke folder yang berisi `bin\winutils.exe`.
* **JARs connector** (letakkan di `framework/jars/`):

  * mongo-spark-connector (cocok versi Spark/Python), contoh `mongo-spark-connector_2.12-3.0.1.jar`
  * mongodb-driver-sync, mongodb-driver-core, bson (jika error ClassNotFound)
  * gcs-connector-hadoop3 (`gcs-connector-hadoop3-2.2.5-shaded.jar`) untuk write ke GCS
* **Google creds**: simpan service account JSON dan set `GOOGLE_APPLICATION_CREDENTIALS`.

# 3) Project skeleton (contoh)

```
data-processing-script/
├─ script/
│  └─ bigquery/L1/from_mongodb/ref_xxx.py   # job entrypoint
├─ framework/
│  ├─ transformation.py
│  └─ connection.py
├─ requirements.txt
├─ .venv/
└─ jars/
   ├─ mongo-spark-connector_2.12-3.0.1.jar
   ├─ mongodb-driver-sync-4.0.5.jar
   └─ gcs-connector-hadoop3-2.2.5-shaded.jar
```

# 4) Contoh `SparkSession` untuk local dev (Python)

```python
from pyspark.sql import SparkSession
spark = (
  SparkSession.builder
    .appName("my-job")
    .master("local[*]")
    .config("spark.jars", ",".join([
        "path/to/jars/mongo-spark-connector_2.12-3.0.1.jar",
        "path/to/jars/mongodb-driver-sync-4.0.5.jar",
        "path/to/jars/bson-4.0.5.jar",
        "path/to/jars/gcs-connector-hadoop3-2.2.5-shaded.jar"
    ]))
    .config("spark.driver.memory", "4g")
    .config("spark.executor.memory", "4g")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)
```

> Catatan: di cluster gunakan `--jars` / `--packages` pada `spark-submit` bukan `spark.jars` jika ingin terdistribusi.

# 5) Struktur kode fungsi (recommended)

Pisahkan job jadi 3 fungsi yang mudah diuji:

```python
def extract(spark):
    return spark.read.format("com.mongodb.spark.sql.DefaultSource") \
        .option("uri", MONGO_URI) \
        .option("database", MONGO_DB) \
        .option("collection", MONGO_COLLECTION) \
        .load()

def transform(df):
    # jangan tulis semua di satu fungsi besar — pecah lagi kalau perlu
    df = standardize_column_spark(df)
    df = fix_void_columns(df)
    # cast timestamp, add surrogate_key, cleanse
    return df

def load(df):
    df.write.mode("overwrite").parquet(GCS_PATH)
```

Satu file entrypoint hanya panggil `extract -> transform -> load`.

# 6) Menangani connector JAR/ClassNotFound (masalah yang kamu alami)

* Jika error `NoClassDefFoundError org/bson/conversions/Bson` atau `WriteModel` → berarti **kamu butuh JAR driver Mongo** (mongodb-driver-sync, mongodb-driver-core, bson) yang cocok versinya.
* Letakkan semua JAR terkait di folder `jars/` dan tambahkan ke `spark.jars` atau gunakan `spark-submit --jars jars/*.jar`.
* Setelah job selesai kadang Spark menyalin JAR ke temp userFiles dan Windows tidak bisa menghapusnya (file lock). Solusi: jalankan spark dengan `local[*]` + set `spark.driver.extraClassPath` atau gunakan `--conf spark.files.overwrite=true` atau jalankan `spark-submit` dari environment elevated/admin. Atau gunakan JAR di classpath global Spark `SPARK_HOME/jars/`.

# 7) Mengatasi Parquet unsupported VOID

* Void/NullType muncul saat Spark schema kolom sepenuhnya `NullType`. Sebelum write ke Parquet harus cast ke `StringType` (kamu sudah buat `fix_void_columns` — letakkan **sebelum** `write`).
* Contoh: `df = fix_void_columns(df)` → lalu `df.write.parquet(...)`.

# 8) Tips memory / performance di local

* Jangan gunakan terlalu banyak partition writer kalau RAM kecil: `.repartition(n)` sesuaikan dengan CPU/RAM.
* Tingkatkan `spark.driver.memory` jika OOM.
* Untuk parquet writer di Windows, panggil `.coalesce(x)` jika menghasilkan terlalu banyak small-files.

# 9) Testing (unit + integration)

* **Unit test** untuk fungsi transform: buat sample small Spark DataFrame dan assert hasil transform.
* Pytest fixture contoh:

```python
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    spark = SparkSession.builder.master("local[2]").appName("test").getOrCreate()
    yield spark
    spark.stop()

def test_transform(spark):
    df = spark.createDataFrame([{"a":1, "ts": None}], ["a","ts"])
    df2 = transform(df)
    assert "surrogate_key" in df2.columns
```

* Untuk integration test gunakan small dataset dan write to local parquet bukan GCS.

# 10) Packaging & deploy

* **Local debug**: `python script/.../job.py` (SparkSession local)
* **Cluster**: `spark-submit --master yarn --deploy-mode cluster --jars jars/*.jar job.py`
* **GCP Dataproc**: gunakan `gcloud dataproc jobs submit pyspark job.py --jars ...`
* **Docker**: paket kode ke image yang berisi Spark runtime (lebih advanced). Biasanya cluster-managed Spark (Dataproc/EMR) lebih praktis.

Contoh `spark-submit` dengan jars:

```bash
spark-submit \
  --master local[*] \
  --conf spark.driver.memory=4g \
  --jars jars/mongo-spark-connector_2.12-3.0.1.jar,jars/mongodb-driver-sync-4.0.5.jar,jars/bson-4.0.5.jar,jars/gcs-connector-hadoop3-2.2.5-shaded.jar \
  script/bigquery/L1/from_mongodb/ref_xxx.py
```

# 11) Streaming vs Batch — apa bedanya dan fokus setup

* **Batch**: read collection/full export → transform → write Parquet/BQ. Idempotency: gunakan surrogate_key & WRITE_TRUNCATE atau merge di target.
* **Structured Streaming**: gunakan Spark Structured Streaming `readStream` → `writeStream` dengan checkpointing. Pastikan: checkpoint dir persisten (GCS/HDFS), watermark sesuai, exactly-once (sink mendukung).

# 12) Logging, secrets & credentials

* Jangan commit service account JSON — gunakan secret manager / env var di production.
* Gunakan logging (python logging) dan simpan logs ke file/Stackdriver/ELK.
* Tambahkan retry pada load job (BigQuery load sometimes transient fail).

# 13) Monitoring & Production Hardening

* Atur alert pada Airflow / monitoring.
* Checkpoints dan idempotency.
* Use schema enforcement (Parquet schema, Avro, or Delta Lake) untuk mutasi kolom.
* Add data quality checks (row counts, null rate) setelah load.

# 14) Common gotchas & troubleshooting (singkat)

* `NoClassDefFoundError` → missing JAR (add driver-core, bson, etc).
* `UNSUPPORTED_DATA_TYPE_FOR_DATASOURCE` (VOID) → cast NullType → String.
* Windows: Spark temp files locked → hapus `%temp%\spark-*` setelah stop, atau jalankan Spark jar dari SPARK_HOME/jars.
* Memory OOM: naikkan `spark.driver.memory` atau kurangi partitions / pembacaan paralel.

# 15) Quick checklist sebelum run pertama

* [ ] Java terpasang & `JAVA_HOME` benar
* [ ] Python venv aktif & `pyspark`/deps terinstal
* [ ] JAR connector ada di `jars/` dan dipasang di spark.jars / --jars
* [ ] `GOOGLE_APPLICATION_CREDENTIALS` set (untuk GCS/BQ)
* [ ] Fix void columns sebelum write
* [ ] Test transform di local dengan small sample
* [ ] Konfig `spark.driver.memory` sesuai RAM

---

Kalau mau, aku bisa langsung:

1. Buatkan **template repo** (file `ref_bahasaai_fondasi_log_api.py` + `requirements.txt` + `Dockerfile` + `pytest` fixture) — siap dipakai.
2. Atau **beri skrip PowerShell** untuk bersihin temp Spark otomatis setelah job (aman).
3. Atau **perbaiki file kamu**: aku kirim patch perubahan yang mesti dilakukan (pastiin `fix_void_columns` dipanggil, set spark.jars, memory configs, handling jar paths).

Mau aku buatkan template repo siap-coba sekarang?