-- External Table
SELECT COUNT(DISTINCT PULocationID) AS distinct_pu_external
FROM `your-project.nytaxi.external_yellow_2024`;

-- Materialized Table
SELECT COUNT(DISTINCT PULocationID) AS distinct_pu_materialized
FROM `your-project.nytaxi.yellow_tripdata_2024`;
