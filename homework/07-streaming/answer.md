# 📚 Homework Week 7 – Stream Processing with PyFlink  
## Data Engineering Zoomcamp 2026

> **Dataset:** Green Taxi Trip October 2025  
> **Stack:** Redpanda (Kafka) · Apache Flink · PostgreSQL · Python

---

## 📋 Table of Contents

1. [Infrastructure Setup](#infrastructure-setup)
2. [Q1 – Redpanda Version](#question-1-redpanda-version)
3. [Q2 – Sending Data to Redpanda](#question-2-sending-data-to-redpanda)
4. [Q3 – Consumer Trip Distance](#question-3-consumer--trip-distance)
5. [Q4 – Tumbling Window Pickup Location](#question-4-tumbling-window--pickup-location)
6. [Q5 – Session Window Longest Streak](#question-5-session-window--longest-streak)
7. [Q6 – Tumbling Window Largest Tip](#question-6-tumbling-window--largest-tip)
8. [Answer Summary](#-answer-summary)

---

## Infrastructure Setup

### 1. Clone the repo and enter the workshop folder

```bash
git clone https://github.com/DataTalksClub/data-engineering-zoomcamp.git
cd data-engineering-zoomcamp/07-streaming/workshop/
```

### 2. Required `src` folder structure

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

### 3. Build Docker images and start all services

If you don't have the images yet or want a clean start:

```bash
docker compose down -v      # remove old containers & volumes
docker compose build        # build custom PyFlink image
docker compose up -d        # start all services
```

### 4. Verify all containers are running

```bash
docker compose ps
```

Expected output:

```
NAME                        IMAGE                           SERVICE        STATUS
workshop-jobmanager-1       pyflink-workshop                jobmanager     Up
workshop-taskmanager-1      pyflink-workshop                taskmanager    Up
workshop-postgres-1         postgres:18                     postgres       Up
workshop-redpanda-1         redpandadata/redpanda:v25.3.9   redpanda       Up
```

### 5. Check Flink Dashboard

Open browser: **http://localhost:8081**  
You should see 1 TaskManager with 15 available task slots.

### 6. Install Python dependencies

```bash
uv add kafka-python pandas pyarrow
```

---

## Question 1. Redpanda Version

### Command

```bash
docker exec -it workshop-redpanda-1 rpk version
```

### Output

```
v25.3.9 (rev bf07a24a4)
```

### ✅ Q1 Answer: `v25.3.9`

---

## Question 2. Sending Data to Redpanda

### Step 1 – Create topic `green-trips`

```bash
docker exec -it workshop-redpanda-1 rpk topic create green-trips
```

Verify the topic exists:

```bash
docker exec -it workshop-redpanda-1 rpk topic list
```

### Step 2 – Create the producer script

Save as `src/producers/producer_green.py`:

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

# ── Convert datetime to string (JSON cannot serialize Timestamp) ──────────
df['lpep_pickup_datetime'] = df['lpep_pickup_datetime'].astype(str)
df['lpep_dropoff_datetime'] = df['lpep_dropoff_datetime'].astype(str)

# ── Send to Kafka ─────────────────────────────────────────────────────────
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

### Step 3 – Run the producer

```bash
uv run python src/producers/producer_green.py
```

Expected output:

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

### ✅ Q2 Answer: **60 seconds**

> The October 2025 Green Taxi dataset contains ~75 thousand rows. Sending time is around 60-65 seconds due to `iterrows()` + network overhead per message.

---

## Question 3. Consumer – Trip Distance

### Create the consumer script

Save as `src/consumers/consumer_green.py`:

```python
"""
Green Taxi Trip Consumer – Homework Q3
Reads all messages from 'green-trips' and counts trip_distance > 5.0
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
    auto_offset_reset='earliest',       # read from the beginning of the topic
    group_id='green-trips-counter',
    value_deserializer=json_deserializer,
    consumer_timeout_ms=5000,           # stop after 5 seconds idle
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

### Run the consumer

```bash
uv run python src/consumers/consumer_green.py
```

Expected output:

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

### ✅ Q3 Answer: **7,506**

---

## Setup PostgreSQL Tables

Before running the Flink jobs, create the required tables in PostgreSQL.

### Connect to PostgreSQL

```bash
# via pgcli
uvx pgcli -h localhost -p 5432 -U postgres -d postgres
# password: postgres
```

or:

```bash
docker compose exec postgres psql -U postgres -d postgres
```

### Create all tables

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

Verify:

```sql
\dt
```

---

## Question 4. Tumbling Window – Pickup Location

### Concept

Flink splits the stream into **fixed 5-minute windows** that do not overlap. Each event belongs to exactly one window based on `event_timestamp`. Result: number of trips per `PULocationID` in each 5-minute window.

```
|-- 00:00-00:05 --|-- 00:05-00:10 --|-- 00:10-00:15 --|
       window 1          window 2          window 3
```

### Create the Flink job

Save as `src/job/q4_tumbling_window.py`:

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
    env.set_parallelism(1)   # ⚠️ must be 1 because the topic has 1 partition

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

### Submit the Flink job

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

Open **http://localhost:8081** → see the job status **RUNNING**. Wait 1-2 minutes until all data is processed.

### Query the results

```sql
SELECT pulocationid, num_trips
FROM pickup_window_counts
ORDER BY num_trips DESC
LIMIT 3;
```

Expected output:

```
 pulocationid | num_trips
--------------+-----------
           74 |        X
           75 |        X
          ...
```

### ✅ Q4 Answer: **PULocationID = 74**

---

## Question 5. Session Window – Longest Streak

### Concept

A session window is **different** from a tumbling window. Windows do not have a fixed size — a window closes when there is a gap of inactivity for a specified period (5 minutes). Events from the same `PULocationID` that are close in time are grouped into one session.

```
|--events--| 5 min gap |--events--| 5 min gap |--events--|
| Session1 |           | Session2 |           | Session3 |
```

Question: which session contains the most trips?

### Create the Flink job

Save as `src/job/q5_session_window.py`:

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
    env.set_parallelism(1)   # ⚠️ must be 1

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

### Submit the Flink job

> ⚠️ Cancel Q4 job from the Flink UI before submitting a new one!

```bash
docker exec -it workshop-jobmanager-1 flink run \
    -py /opt/src/job/q5_session_window.py \
    --pyFiles /opt/src -d
```

### Query the results

```sql
SELECT pulocationid, num_trips, window_start, window_end
FROM pickup_session_counts
ORDER BY num_trips DESC
LIMIT 5;
```

Expected output:

```
 pulocationid | num_trips |     window_start      |      window_end
--------------+-----------+-----------------------+-----------------------
          XXX |        51 | 2025-10-XX XX:XX:XX   | 2025-10-XX XX:XX:XX
          ...
```

### ✅ Q5 Answer: **51 trips** (longest session)

---

## Question 6. Tumbling Window – Largest Tip

### Concept

1-hour tumbling window, calculating the **total `tip_amount`** across all locations in each hour. We find the hour with the highest total tip.

```
| 00:00-01:00 | 01:00-02:00 | 02:00-03:00 | ... |
     SUM tip       SUM tip       SUM tip
```

### Create the Flink job

Save as `src/job/q6_hourly_tip.py`:

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

### Submit the Flink job

> ⚠️ Cancel Q5 job from the Flink UI first!

```bash
docker exec -it workshop-jobmanager-1 flink run \
    -py /opt/src/job/q6_hourly_tip.py \
    --pyFiles /opt/src -d
```

### Query the results

```sql
SELECT window_start, ROUND(total_tip::numeric, 2) AS total_tip
FROM hourly_tip_totals
ORDER BY total_tip DESC
LIMIT 5;
```

Expected output:

```
     window_start      | total_tip
-----------------------+-----------
 2025-10-01 18:00:00   |   XXXX.XX   ← highest
 2025-10-01 19:00:00   |   XXXX.XX
 ...
```

### ✅ Q6 Answer: **2025-10-01 18:00:00**

---

## ⚠️ Tips & Troubleshooting

### 1. Watermark not advancing – job stuck

**Cause:** Parallelism > 1 on a topic with 1 partition. Idle tasks do not emit watermarks, so the global watermark never advances and windows never close.

**Solution:** Always set `env.set_parallelism(1)` for topics with 1 partition.

### 2. Duplicate data in PostgreSQL

If the producer is run more than once, the topic will contain duplicate data.

```bash
# Delete and recreate the topic
docker exec -it workshop-redpanda-1 rpk topic delete green-trips
docker exec -it workshop-redpanda-1 rpk topic create green-trips

# Run the producer again
uv run python src/producers/producer_green.py
```

### 3. Flink job won't start

Make sure no other job is running simultaneously. Cancel from the UI **http://localhost:8081** → Jobs → Running → Cancel.

### 4. Datetime format error

Timestamps in the parquet file are formatted as `2025-10-01 00:00:00`. The DDL uses `'yyyy-MM-dd HH:mm:ss'` which matches.

### 5. How to check topics and offsets

```bash
# List all topics
docker exec -it workshop-redpanda-1 rpk topic list

# Show topic details (number of messages)
docker exec -it workshop-redpanda-1 rpk topic describe green-trips
```

### 6. Reset PostgreSQL tables before re-running a job

```sql
TRUNCATE pickup_window_counts;
TRUNCATE pickup_session_counts;
TRUNCATE hourly_tip_totals;
```

---

## 🏁 Answer Summary

| # | Question | Answer |
|---|----------|--------|
| **Q1** | Redpanda version | **v25.3.9** |
| **Q2** | Time to send data to Redpanda | **60 seconds** |
| **Q3** | Number of trips with `trip_distance > 5` | **7,506** |
| **Q4** | `PULocationID` with most trips in a single 5‑minute window | **74** |
| **Q5** | Number of trips in the longest session | **51** |
| **Q6** | Hour with the highest total tip | **2025-10-01 18:00:00** |

---

## References

- [PyFlink Workshop README](https://github.com/DataTalksClub/data-engineering-zoomcamp/tree/main/07-streaming/workshop)
- [Apache Flink Table API – Windows](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/table/sql/queries/window-tvf/)
- [Redpanda Documentation](https://docs.redpanda.com/)
- [Submission Form](https://courses.datatalks.club/de-zoomcamp-2026/homework/hw7)