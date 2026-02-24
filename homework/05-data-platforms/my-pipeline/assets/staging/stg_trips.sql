/* @bruin
name: staging.stg_trips
type: duckdb.sql
connection: duckdb-default

materialization:
  type: table
  strategy: time_interval
  incremental_key: pickup_datetime
  time_granularity: month

depends:
  - nyc_raw.trips
*/

SELECT
    pickup_datetime,
    dropoff_datetime,
    passenger_count,
    trip_distance,
    DATE_TRUNC('month', pickup_datetime) AS trip_month
FROM raw_trips
WHERE pickup_datetime BETWEEN {{ start_date }} AND {{ end_date }};