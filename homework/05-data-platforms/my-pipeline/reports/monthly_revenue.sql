/* @bruin
name: mart.monthly_revenue
type: duckdb.sql
connection: duckdb-default

materialization:
  type: table

depends:
  - staging.stg_trips
*/

SELECT
    trip_month,
    COUNT(*) AS total_trips,
    SUM(trip_distance) AS total_distance
FROM staging.stg_trips
GROUP BY 1
ORDER BY 1;