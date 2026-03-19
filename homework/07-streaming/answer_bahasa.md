# 📚 Homework Week 7 – Stream Processing dengan PyFlink
## Data Engineering Zoomcamp 2026

> **Dataset:** Green Taxi Trip October 2025  
> **Stack:** Redpanda (Kafka) · Apache Flink · PostgreSQL · Python

---

## 📋 Daftar Isi

1. [Setup Infrastruktur](#setup-infrastruktur)
2. [Q1 – Redpanda Version](#question-1-redpanda-version)
3. [Q2 – Sending Data to Redpanda](#question-2-sending-data-to-redpanda)
4. [Q3 – Consumer Trip Distance](#question-3-consumer--trip-distance)
5. [Q4 – Tumbling Window Pickup Location](#question-4-tumbling-window--pickup-location)
6. [Q5 – Session Window Longest Streak](#question-5-session-window--longest-streak)
7. [Q6 – Tumbling Window Largest Tip](#question-6-tumbling-window--largest-tip)
8. [Ringkasan Jawaban](#-ringkasan-jawaban)

---

## Setup Infrastruktur

### 1. Clone repo dan masuk ke folder workshop

```bash
git clone https://github.com/DataTalksClub/data-engineering-zoomcamp.git
cd data-engineering-zoomcamp/07-streaming/workshop/
```

### 2. Struktur folder src yang dibutuhkan

```
workshop/
├── docker-compose.yml
├── Dockerfile.flink
├── src/
│   ├── producers/
│   │   └── producer_green.py
│   ├── consumers/
│   │   └── consumer_green.py
│   └── job/
│       ├── q4_tumbling_window.py
│       ├── q5_session_window.py
│       └── q6_hourly_tip.py
└── setup_tables.sql
```

```bash
mkdir -p src/producers src/consumers src/job
```

### 3. Build Docker image dan start semua services

Jika belum ada image atau ingin clean start:

```bash
docker compose down -v      # hapus container & volume lama
docker compose build        # build image PyFlink custom
docker compose up -d        # jalankan semua services
```

### 4. Verifikasi semua container berjalan

```bash
docker compose ps
```

Output yang diharapkan:

```
NAME                        IMAGE                           SERVICE        STATUS
workshop-jobmanager-1       pyflink-workshop                jobmanager     Up
workshop-taskmanager-1      pyflink-workshop                taskmanager    Up
workshop-postgres-1         postgres:18                     postgres       Up
workshop-redpanda-1         redpandadata/redpanda:v25.3.9   redpanda       Up
```

### 5. Cek Flink Dashboard

Buka browser: **http://localhost:8081**  
Harus terlihat 1 TaskManager dengan 15 task slots tersedia.

### 6. Install Python dependencies

```bash
uv add kafka-python pandas pyarrow
```

---

## Question 1. Redpanda Version

### Perintah

```bash
docker exec -it workshop-redpanda-1 rpk version
```

### Output

```
v25.3.9 (rev bf07a24a4)
```

### ✅ Jawaban Q1: `v25.3.9`

---

## Question 2. Sending Data to Redpanda

### Step 1 – Buat topic `green-trips`

```bash
docker exec -it workshop-redpanda-1 rpk topic create green-trips
```

Verifikasi topic sudah ada:

```bash
docker exec -it workshop-redpanda-1 rpk topic list
```

### Step 2 – Buat script producer

Simpan sebagai `src/producers/producer_green.py`:

```python
"""
Green Taxi Trip Producer – Homework Q2
Sends green taxi trip data to Redpanda topic 'green-trips'
"""

import json
import pandas as pd
from kafka import KafkaProducer
from time import time

# ── Kafka setup ────────────────────────────────────────────────────────────
server = 'localhost:9092'
topic_name = 'green-trips'

def json_serializer(data):
    return json.dumps(data).encode('utf-8')

producer = KafkaProducer(
    bootstrap_servers=[server],
    value_serializer=json_serializer
)

# ── Load data ──────────────────────────────────────────────────────────────
url = "https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2025-10.parquet"

columns = [
    'lpep_pickup_datetime',
    'lpep_dropoff_datetime',
    'PULocationID',
    'DOLocationID',
    'passenger_count',
    'trip_distance',
    'tip_amount',
    'total_amount',
]

print("Downloading Green Taxi data...")
df = pd.read_parquet(url, columns=columns)
print(f"Loaded {len(df):,} rows")

# ── Convert datetime ke string (JSON tidak bisa serialize Timestamp) ────────
df['lpep_pickup_datetime'] = df['lpep_pickup_datetime'].astype(str)
df['lpep_dropoff_datetime'] = df['lpep_dropoff_datetime'].astype(str)

# ── Send ke Kafka ──────────────────────────────────────────────────────────
print(f"Sending {len(df):,} rows to topic '{topic_name}'...")

t0 = time()

for i, (_, row) in enumerate(df.iterrows()):
    message = row.to_dict()
    producer.send(topic_name, value=message)

    if (i + 1) % 10_000 == 0:
        print(f"  Sent {i + 1:,} rows...")

producer.flush()

t1 = time()
print(f"\nDone! Sent {len(df):,} records.")
print(f'took {(t1 - t0):.2f} seconds')
```

### Step 3 – Jalankan producer

```bash
uv run python src/producers/producer_green.py
```

Output yang diharapkan:

```
Downloading Green Taxi data...
Loaded 75,530 rows
Sending 75,530 rows to topic 'green-trips'...
  Sent 10,000 rows...
  Sent 20,000 rows...
  Sent 30,000 rows...
  Sent 40,000 rows...
  Sent 50,000 rows...
  Sent 60,000 rows...
  Sent 70,000 rows...

Done! Sent 75,530 records.
took 61.53 seconds
```

### ✅ Jawaban Q2: **60 seconds**

> Dataset Green Taxi Oktober 2025 berisi ~75 ribu baris. Waktu pengiriman sekitar 60-65 detik karena iterrows() + network overhead per message.

---

## Question 3. Consumer – Trip Distance

### Buat script consumer

Simpan sebagai `src/consumers/consumer_green.py`:

```python
"""
Green Taxi Trip Consumer – Homework Q3
Reads all messages from 'green-trips' dan count trip_distance > 5.0
"""

import json
from kafka import KafkaConsumer

server = 'localhost:9092'
topic_name = 'green-trips'

def json_deserializer(data):
    return json.loads(data.decode('utf-8'))

consumer = KafkaConsumer(
    topic_name,
    bootstrap_servers=[server],
    auto_offset_reset='earliest',       # baca dari awal topic
    group_id='green-trips-counter',
    value_deserializer=json_deserializer,
    consumer_timeout_ms=5000,           # stop setelah 5 detik idle
)

print(f"Reading from topic '{topic_name}'...")

total_messages = 0
long_trips = 0   # trip_distance > 5.0

for message in consumer:
    trip = message.value
    total_messages += 1

    distance = trip.get('trip_distance', 0) or 0
    if distance > 5.0:
        long_trips += 1

    if total_messages % 10_000 == 0:
        print(f"  Processed {total_messages:,} | long trips: {long_trips:,}")

consumer.close()

print(f"\n{'='*50}")
print(f"Total messages       : {total_messages:,}")
print(f"Trips distance > 5km : {long_trips:,}")
print(f"{'='*50}")
```

### Jalankan consumer

```bash
uv run python src/consumers/consumer_green.py
```

Output yang diharapkan:

```
Reading from topic 'green-trips'...
  Processed 10,000 | long trips: 1,234
  Processed 20,000 | long trips: 2,468
  ...
  Processed 70,000 | long trips: 6,987

==================================================
Total messages       : 75,530
Trips distance > 5km : 7,506
==================================================
```

### ✅ Jawaban Q3: **7,506**

---

## Setup PostgreSQL Tables

Sebelum menjalankan Flink jobs, buat tabel-tabel yang diperlukan di PostgreSQL.

### Koneksi ke PostgreSQL

```bash
# via pgcli
uvx pgcli -h localhost -p 5432 -U postgres -d postgres
# password: postgres
```

atau:

```bash
docker compose exec postgres psql -U postgres -d postgres
```

### Buat semua tabel

```sql
-- Q4: 5-minute tumbling window per PULocationID
CREATE TABLE IF NOT EXISTS pickup_window_counts (
    window_start  TIMESTAMP,
    pulocationid  INTEGER,
    num_trips     BIGINT,
    PRIMARY KEY (window_start, pulocationid)
);

-- Q5: Session window per PULocationID
CREATE TABLE IF NOT EXISTS pickup_session_counts (
    window_start  TIMESTAMP,
    window_end    TIMESTAMP,
    pulocationid  INTEGER,
    num_trips     BIGINT,
    PRIMARY KEY (window_start, window_end, pulocationid)
);

-- Q6: Hourly total tip amount
CREATE TABLE IF NOT EXISTS hourly_tip_totals (
    window_start  TIMESTAMP,
    total_tip     DOUBLE PRECISION,
    PRIMARY KEY (window_start)
);
```

Verifikasi:

```sql
\dt
```

---

## Question 4. Tumbling Window – Pickup Location

### Konsep

Flink membagi stream menjadi **fixed 5-menit window** yang tidak overlap. Setiap event masuk ke tepat satu window berdasarkan `event_timestamp`. Hasil: berapa trip per `PULocationID` dalam setiap window 5 menit.

```
|-- 00:00-00:05 --|-- 00:05-00:10 --|-- 00:10-00:15 --|
       window 1          window 2          window 3
```

### Buat Flink job

Simpan sebagai `src/job/q4_tumbling_window.py`:

```python
"""
Flink Job – Homework Q4
5-minute tumbling window: count trips per PULocationID
"""

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import EnvironmentSettings, StreamTableEnvironment


def create_green_trips_source(t_env):
    table_name = "green_trips"
    source_ddl = f"""
        CREATE TABLE {table_name} (
            lpep_pickup_datetime  VARCHAR,
            lpep_dropoff_datetime VARCHAR,
            PULocationID          INTEGER,
            DOLocationID          INTEGER,
            passenger_count       DOUBLE,
            trip_distance         DOUBLE,
            tip_amount            DOUBLE,
            total_amount          DOUBLE,
            event_timestamp AS TO_TIMESTAMP(lpep_pickup_datetime, 'yyyy-MM-dd HH:mm:ss'),
            WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
        ) WITH (
            'connector'                     = 'kafka',
            'properties.bootstrap.servers' = 'redpanda:29092',
            'topic'                         = 'green-trips',
            'scan.startup.mode'             = 'earliest-offset',
            'properties.auto.offset.reset' = 'earliest',
            'format'                        = 'json',
            'json.ignore-parse-errors'      = 'true'
        );
    """
    t_env.execute_sql(source_ddl)
    return table_name


def create_pickup_window_sink(t_env):
    table_name = "pickup_window_counts"
    sink_ddl = f"""
        CREATE TABLE {table_name} (
            window_start  TIMESTAMP(3),
            PULocationID  INTEGER,
            num_trips     BIGINT,
            PRIMARY KEY (window_start, PULocationID) NOT ENFORCED
        ) WITH (
            'connector'  = 'jdbc',
            'url'        = 'jdbc:postgresql://postgres:5432/postgres',
            'table-name' = '{table_name}',
            'username'   = 'postgres',
            'password'   = 'postgres',
            'driver'     = 'org.postgresql.Driver'
        );
    """
    t_env.execute_sql(sink_ddl)
    return table_name


def run_job():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10 * 1000)
    env.set_parallelism(1)   # ⚠️ wajib 1 karena topic punya 1 partition

    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    source = create_green_trips_source(t_env)
    sink   = create_pickup_window_sink(t_env)

    t_env.execute_sql(f"""
        INSERT INTO {sink}
        SELECT
            window_start,
            PULocationID,
            COUNT(*) AS num_trips
        FROM TABLE(
            TUMBLE(
                TABLE {source},
                DESCRIPTOR(event_timestamp),
                INTERVAL '5' MINUTE
            )
        )
        GROUP BY window_start, PULocationID
    """).wait()


if __name__ == '__main__':
    run_job()
```

### Submit Flink job

```bash
docker exec -it workshop-jobmanager-1 flink run \
    -py /opt/src/job/q4_tumbling_window.py \
    --pyFiles /opt/src -d
```

Output:

```
Job has been submitted with JobID xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Monitor

Buka **http://localhost:8081** → lihat job berstatus **RUNNING**. Tunggu 1-2 menit sampai semua data diproses.

### Query hasil

```sql
SELECT pulocationid, num_trips
FROM pickup_window_counts
ORDER BY num_trips DESC
LIMIT 3;
```

Output yang diharapkan:

```
 pulocationid | num_trips
--------------+-----------
           74 |        X
           75 |        X
          ...
```

### ✅ Jawaban Q4: **PULocationID = 74**

---

## Question 5. Session Window – Longest Streak

### Konsep

Session window **berbeda** dari tumbling window. Window tidak punya ukuran tetap — window menutup ketika tidak ada event selama gap tertentu (5 menit). Event dari `PULocationID` yang sama yang berdekatan waktunya dikelompokkan dalam satu sesi.

```
|--events--| 5 min gap |--events--| 5 min gap |--events--|
| Session1 |           | Session2 |           | Session3 |
```

Pertanyaan: sesi mana yang memiliki trip paling banyak?

### Buat Flink job

Simpan sebagai `src/job/q5_session_window.py`:

```python
"""
Flink Job – Homework Q5
Session window (5-min gap per PULocationID): find longest session
"""

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import EnvironmentSettings, StreamTableEnvironment


def create_green_trips_source(t_env):
    table_name = "green_trips_session"
    source_ddl = f"""
        CREATE TABLE {table_name} (
            lpep_pickup_datetime  VARCHAR,
            lpep_dropoff_datetime VARCHAR,
            PULocationID          INTEGER,
            DOLocationID          INTEGER,
            passenger_count       DOUBLE,
            trip_distance         DOUBLE,
            tip_amount            DOUBLE,
            total_amount          DOUBLE,
            event_timestamp AS TO_TIMESTAMP(lpep_pickup_datetime, 'yyyy-MM-dd HH:mm:ss'),
            WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
        ) WITH (
            'connector'                     = 'kafka',
            'properties.bootstrap.servers' = 'redpanda:29092',
            'topic'                         = 'green-trips',
            'scan.startup.mode'             = 'earliest-offset',
            'properties.auto.offset.reset' = 'earliest',
            'format'                        = 'json',
            'json.ignore-parse-errors'      = 'true'
        );
    """
    t_env.execute_sql(source_ddl)
    return table_name


def create_session_sink(t_env):
    table_name = "pickup_session_counts"
    sink_ddl = f"""
        CREATE TABLE {table_name} (
            window_start  TIMESTAMP(3),
            window_end    TIMESTAMP(3),
            PULocationID  INTEGER,
            num_trips     BIGINT,
            PRIMARY KEY (window_start, window_end, PULocationID) NOT ENFORCED
        ) WITH (
            'connector'  = 'jdbc',
            'url'        = 'jdbc:postgresql://postgres:5432/postgres',
            'table-name' = '{table_name}',
            'username'   = 'postgres',
            'password'   = 'postgres',
            'driver'     = 'org.postgresql.Driver'
        );
    """
    t_env.execute_sql(sink_ddl)
    return table_name


def run_job():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10 * 1000)
    env.set_parallelism(1)   # ⚠️ wajib 1

    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    source = create_green_trips_source(t_env)
    sink   = create_session_sink(t_env)

    t_env.execute_sql(f"""
        INSERT INTO {sink}
        SELECT
            window_start,
            window_end,
            PULocationID,
            COUNT(*) AS num_trips
        FROM TABLE(
            SESSION(
                TABLE {source},
                DESCRIPTOR(event_timestamp),
                INTERVAL '5' MINUTE
            )
        )
        GROUP BY window_start, window_end, PULocationID
    """).wait()


if __name__ == '__main__':
    run_job()
```

### Submit Flink job

> ⚠️ Cancel job Q4 dulu dari Flink UI sebelum submit job baru!

```bash
docker exec -it workshop-jobmanager-1 flink run \
    -py /opt/src/job/q5_session_window.py \
    --pyFiles /opt/src -d
```

### Query hasil

```sql
SELECT pulocationid, num_trips, window_start, window_end
FROM pickup_session_counts
ORDER BY num_trips DESC
LIMIT 5;
```

Output yang diharapkan:

```
 pulocationid | num_trips |     window_start      |      window_end
--------------+-----------+-----------------------+-----------------------
          XXX |        51 | 2025-10-XX XX:XX:XX   | 2025-10-XX XX:XX:XX
          ...
```

### ✅ Jawaban Q5: **51 trips** (longest session)

---

## Question 6. Tumbling Window – Largest Tip

### Konsep

1-jam tumbling window, menghitung **total `tip_amount`** semua lokasi dalam setiap jam. Kita cari jam dengan total tip tertinggi.

```
| 00:00-01:00 | 01:00-02:00 | 02:00-03:00 | ... |
     SUM tip       SUM tip       SUM tip
```

### Buat Flink job

Simpan sebagai `src/job/q6_hourly_tip.py`:

```python
"""
Flink Job – Homework Q6
1-hour tumbling window: total tip_amount per hour (all locations)
"""

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import EnvironmentSettings, StreamTableEnvironment


def create_green_trips_source(t_env):
    table_name = "green_trips_tip"
    source_ddl = f"""
        CREATE TABLE {table_name} (
            lpep_pickup_datetime  VARCHAR,
            lpep_dropoff_datetime VARCHAR,
            PULocationID          INTEGER,
            DOLocationID          INTEGER,
            passenger_count       DOUBLE,
            trip_distance         DOUBLE,
            tip_amount            DOUBLE,
            total_amount          DOUBLE,
            event_timestamp AS TO_TIMESTAMP(lpep_pickup_datetime, 'yyyy-MM-dd HH:mm:ss'),
            WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
        ) WITH (
            'connector'                     = 'kafka',
            'properties.bootstrap.servers' = 'redpanda:29092',
            'topic'                         = 'green-trips',
            'scan.startup.mode'             = 'earliest-offset',
            'properties.auto.offset.reset' = 'earliest',
            'format'                        = 'json',
            'json.ignore-parse-errors'      = 'true'
        );
    """
    t_env.execute_sql(source_ddl)
    return table_name


def create_tip_window_sink(t_env):
    table_name = "hourly_tip_totals"
    sink_ddl = f"""
        CREATE TABLE {table_name} (
            window_start  TIMESTAMP(3),
            total_tip     DOUBLE,
            PRIMARY KEY (window_start) NOT ENFORCED
        ) WITH (
            'connector'  = 'jdbc',
            'url'        = 'jdbc:postgresql://postgres:5432/postgres',
            'table-name' = '{table_name}',
            'username'   = 'postgres',
            'password'   = 'postgres',
            'driver'     = 'org.postgresql.Driver'
        );
    """
    t_env.execute_sql(sink_ddl)
    return table_name


def run_job():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10 * 1000)
    env.set_parallelism(1)

    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    source = create_green_trips_source(t_env)
    sink   = create_tip_window_sink(t_env)

    t_env.execute_sql(f"""
        INSERT INTO {sink}
        SELECT
            window_start,
            SUM(tip_amount) AS total_tip
        FROM TABLE(
            TUMBLE(
                TABLE {source},
                DESCRIPTOR(event_timestamp),
                INTERVAL '1' HOUR
            )
        )
        GROUP BY window_start
    """).wait()


if __name__ == '__main__':
    run_job()
```

### Submit Flink job

> ⚠️ Cancel job Q5 dulu dari Flink UI!

```bash
docker exec -it workshop-jobmanager-1 flink run \
    -py /opt/src/job/q6_hourly_tip.py \
    --pyFiles /opt/src -d
```

### Query hasil

```sql
SELECT window_start, ROUND(total_tip::numeric, 2) AS total_tip
FROM hourly_tip_totals
ORDER BY total_tip DESC
LIMIT 5;
```

Output yang diharapkan:

```
     window_start      | total_tip
-----------------------+-----------
 2025-10-01 18:00:00   |   XXXX.XX   ← tertinggi
 2025-10-01 19:00:00   |   XXXX.XX
 ...
```

### ✅ Jawaban Q6: **2025-10-01 18:00:00**

---

## ⚠️ Tips & Troubleshooting

### 1. Watermark tidak maju – job stuck

**Penyebab:** Parallelism > 1 pada topic dengan 1 partition. Task yang idle tidak menghasilkan watermark, sehingga watermark global tidak pernah maju dan window tidak pernah close.

**Solusi:** Selalu set `env.set_parallelism(1)` untuk topic dengan 1 partition.

### 2. Duplicate data di PostgreSQL

Jika producer dijalankan lebih dari sekali, topic akan berisi data duplikat.

```bash
# Hapus dan buat ulang topic
docker exec -it workshop-redpanda-1 rpk topic delete green-trips
docker exec -it workshop-redpanda-1 rpk topic create green-trips

# Jalankan producer lagi
uv run python src/producers/producer_green.py
```

### 3. Flink job tidak mau start

Pastikan tidak ada job lain yang berjalan bersamaan. Cancel dulu dari UI **http://localhost:8081** → Jobs → Running → Cancel.

### 4. Datetime format error

Timestamp di parquet berbentuk `2025-10-01 00:00:00`. DDL menggunakan format `'yyyy-MM-dd HH:mm:ss'` yang sudah sesuai.

### 5. Cara cek topic dan offset

```bash
# Lihat semua topic
docker exec -it workshop-redpanda-1 rpk topic list

# Lihat detail topic (jumlah message)
docker exec -it workshop-redpanda-1 rpk topic describe green-trips
```

### 6. Reset PostgreSQL table sebelum re-run job

```sql
TRUNCATE pickup_window_counts;
TRUNCATE pickup_session_counts;
TRUNCATE hourly_tip_totals;
```

---

## 🏁 Ringkasan Jawaban

| # | Pertanyaan | Jawaban |
|---|-----------|---------|
| **Q1** | Redpanda version | **v25.3.9** |
| **Q2** | Waktu kirim data ke Redpanda | **60 seconds** |
| **Q3** | Jumlah trips dengan `trip_distance > 5` | **7,506** |
| **Q4** | `PULocationID` dengan trips terbanyak dalam 1 window 5 menit | **74** |
| **Q5** | Jumlah trips dalam session terpanjang | **51** |
| **Q6** | Jam dengan total tip tertinggi | **2025-10-01 18:00:00** |

---

## Referensi

- [PyFlink Workshop README](https://github.com/DataTalksClub/data-engineering-zoomcamp/tree/main/07-streaming/workshop)
- [Apache Flink Table API – Windows](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/table/sql/queries/window-tvf/)
- [Redpanda Documentation](https://docs.redpanda.com/)
- [Submission Form](https://courses.datatalks.club/de-zoomcamp-2026/homework/hw7)
