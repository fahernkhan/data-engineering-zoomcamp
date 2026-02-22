# Module 1 Homework: Docker & SQL - Complete Solution

## Overview
This repository contains the complete solution for Module 1 Homework of the Data Engineering Zoomcamp 2026. The homework covers Docker, PostgreSQL, SQL analytics, and Terraform fundamentals.

## Prerequisites
- Docker and Docker Compose installed
- Python 3.13+ with pip
- Git for version control
- Access to terminal (WSL/Linux/macOS)

## Question 1: Understanding Docker Images

### Problem
Run docker with the `python:3.13` image using `bash` as entrypoint and determine the `pip` version.

### Solution
```bash
# Run Python container interactively
docker run -it --entrypoint=bash python:3.13

# Inside container, check pip version
pip --version
```

### Output
```
pip 25.3 from /usr/local/lib/python3.13/site-packages/pip (python 3.13)
```

### Answer: **25.3**

---

## Question 2: Docker Networking & docker-compose

### Problem
Given the `docker-compose.yaml`, determine the `hostname` and `port` that pgadmin should use to connect to Postgres.

### Solution
Analyze the docker-compose file:
- Postgres service name: `db`
- Internal Postgres port: `5432`
- pgAdmin connects using service name within Docker network

### Answer: **db:5432**

---

## Data Preparation

### Download Required Data
```bash
# Download green taxi trips for November 2025
wget https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2025-11.parquet

# Download taxi zone lookup data
wget https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/taxi_zone_lookup.csv
```

---

## Database Setup

### 1. Create docker-compose.yaml
```yaml
services:
  db:
    container_name: postgres
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: 'postgres'
      POSTGRES_PASSWORD: 'postgres'
      POSTGRES_DB: 'ny_taxi'
    ports:
      - '5433:5432'
    volumes:
      - vol-pgdata:/var/lib/postgresql/data

  pgadmin:
    container_name: pgadmin
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: "pgadmin@pgadmin.com"
      PGADMIN_DEFAULT_PASSWORD: "pgadmin"
    ports:
      - "8080:80"
    volumes:
      - vol-pgadmin_data:/var/lib/pgadmin

volumes:
  vol-pgdata:
    name: vol-pgdata
  vol-pgadmin_data:
    name: vol-pgadmin_data
```

### 2. Start Services
```bash
docker compose up -d
```

### 3. Verify Running Containers
```bash
docker ps
```

### 4. Load Zone Data into Postgres
```bash
# Copy CSV file to container
docker cp taxi_zone_lookup.csv postgres:/tmp/taxi_zone_lookup.csv

# Connect to PostgreSQL
docker exec -it postgres psql -U postgres -d ny_taxi
```

Inside PostgreSQL:
```sql
-- Create zone table (lowercase column names as per Postgres convention)
CREATE TABLE taxi_zone_lookup (
  locationid INT,
  borough TEXT,
  zone TEXT,
  service_zone TEXT
);

-- Load CSV data
COPY taxi_zone_lookup
FROM '/tmp/taxi_zone_lookup.csv'
DELIMITER ','
CSV HEADER;

-- Verify data
SELECT COUNT(*) FROM taxi_zone_lookup;  -- Should return 265 rows
```

### 5. Load Trip Data (Parquet to Postgres)
Create `load_green_tripdata.py`:
```python
import pandas as pd
from sqlalchemy import create_engine

# Create connection to PostgreSQL
engine = create_engine("postgresql://postgres:postgres@localhost:5433/ny_taxi")

# Read parquet file
df = pd.read_parquet("green_tripdata_2025-11.parquet")

# Load into PostgreSQL
df.to_sql("green_tripdata", engine, if_exists="replace", index=False)

print(f"Rows loaded: {len(df)}")  # Should show 46,912 rows
```

Run the script:
```bash
python load_green_tripdata.py
```

---

## Question 3: Counting Short Trips

### Problem
Count trips with `trip_distance` ≤ 1 mile in November 2025.

### SQL Query
```sql
SELECT COUNT(1) AS short_trips
FROM green_tripdata
WHERE lpep_pickup_datetime >= '2025-11-01'
  AND lpep_pickup_datetime < '2025-12-01'
  AND trip_distance <= 1;
```

### Output: **8,007**

### Answer: **8,007**

---

## Question 4: Longest Trip for Each Day

### Problem
Find the pickup day with the longest trip distance (excluding trips ≥ 100 miles).

### SQL Query
```sql
SELECT 
  DATE(lpep_pickup_datetime) AS pickup_date,
  MAX(trip_distance) AS max_distance
FROM green_tripdata
WHERE trip_distance < 100
GROUP BY DATE(lpep_pickup_datetime)
ORDER BY max_distance DESC
LIMIT 1;
```

### Output: **2025-11-14**

### Answer: **2025-11-14**

---

## Question 5: Biggest Pickup Zone

### Problem
Find the pickup zone with the largest `total_amount` on November 18, 2025.

### SQL Query
```sql
SELECT
  z.zone AS pickup_zone,
  SUM(g.total_amount) AS total_amount
FROM green_tripdata g
JOIN taxi_zone_lookup z ON g."PULocationID" = z.locationid
WHERE DATE(g.lpep_pickup_datetime) = '2025-11-18'
GROUP BY z.zone
ORDER BY total_amount DESC
LIMIT 1;
```

### Output: **East Harlem North**

### Answer: **East Harlem North**

---

## Question 6: Largest Tip

### Problem
For passengers picked up in "East Harlem North" in November 2025, find the drop-off zone with the largest tip.

### SQL Query
```sql
SELECT
  z2.zone AS dropoff_zone,
  MAX(g.tip_amount) AS max_tip
FROM green_tripdata g
JOIN taxi_zone_lookup z1 ON g."PULocationID" = z1.locationid
JOIN taxi_zone_lookup z2 ON g."DOLocationID" = z2.locationid
WHERE z1.zone = 'East Harlem North'
  AND g.lpep_pickup_datetime >= '2025-11-01'
  AND g.lpep_pickup_datetime < '2025-12-01'
GROUP BY z2.zone
ORDER BY max_tip DESC
LIMIT 1;
```

### Output: **Yorkville West**

### Answer: **Yorkville West**

---

## Question 7: Terraform Workflow

### Problem
Identify the correct Terraform workflow sequence.

### Solution
The correct Terraform workflow is:
1. `terraform init` - Downloads provider plugins and sets up backend
2. `terraform apply -auto-approve` - Generates and auto-executes the plan
3. `terraform destroy` - Removes all resources managed by Terraform

### Answer: **terraform init, terraform apply -auto-approve, terraform destroy**

---

## Summary of Answers

| Question | Answer |
|----------|--------|
| Q1 | 25.3 |
| Q2 | db:5432 |
| Q3 | 8,007 |
| Q4 | 2025-11-14 |
| Q5 | East Harlem North |
| Q6 | Yorkville West |
| Q7 | terraform init, terraform apply -auto-approve, terraform destroy |

---

## Key Learnings

### Docker & Docker Compose
1. **Container Networking**: Containers in the same Docker network can communicate using service names
2. **Port Mapping**: Host port 5433 maps to container port 5432 (`host:container`)
3. **Volume Persistence**: Data persists across container restarts when using volumes

### PostgreSQL & Data Loading
1. **Schema Design**: Postgres defaults to lowercase column names unless quoted
2. **Data Types**: Proper data type selection impacts storage and query performance
3. **Data Import**: Different approaches for CSV (COPY) vs Parquet (Python/pandas)

### SQL Analytics
1. **Date Filtering**: Use `>=` and `<` for inclusive/exclusive date ranges
2. **Aggregation**: GROUP BY with SUM, MAX, COUNT for analytical queries
3. **Joins**: INNER JOIN to combine trip data with zone lookup tables
4. **Column References**: Use double quotes for case-sensitive column names from pandas

### Common Pitfalls & Solutions
1. **Case Sensitivity**: Pandas creates CamelCase columns → use `"PULocationID"` in SQL
2. **Schema Mismatch**: Always verify table schemas with `\d tablename` in psql
3. **Date Handling**: Use `DATE()` function to extract date part from timestamps
4. **Data Validation**: Always check row counts after loading data

### Terraform
1. **Workflow Order**: init → plan → apply → destroy
2. **State Management**: Terraform maintains state file to track infrastructure
3. **Automation**: Use `-auto-approve` for automated deployments

---

## Repository Structure
```
module1-homework/
├── README.md                 # This file
├── docker-compose.yaml       # Docker Compose configuration
├── green_tripdata_2025-11.parquet  # Trip data (downloaded)
├── taxi_zone_lookup.csv      # Zone data (downloaded)
├── load_green_tripdata.py    # Python script to load parquet data
└── queries/                  # SQL query files
    ├── q3_short_trips.sql
    ├── q4_longest_trip.sql
    ├── q5_biggest_pickup.sql
    └── q6_largest_tip.sql
```

---

## Verification Steps
To verify the solution works:
1. Run `docker compose up -d` to start services
2. Execute `load_green_tripdata.py` to load trip data
3. Connect to PostgreSQL and run the SQL queries
4. Compare results with the answers above

---

## Submission
Submit the homework using the form: https://courses.datatalks.club/de-zoomcamp-2026/homework/hw1

Include a link to this GitHub repository in your submission.

---

## Learning in Public
Consider sharing your learning journey on social media using the examples provided in the homework instructions. This helps build accountability, receive feedback, and connect with the data engineering community.

---

*This solution was completed as part of the Data Engineering Zoomcamp 2026. All queries and answers are based on actual execution with the provided datasets.*