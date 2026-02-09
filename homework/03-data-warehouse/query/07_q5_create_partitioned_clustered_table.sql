CREATE OR REPLACE TABLE
  `your-project.nytaxi.yellow_tripdata_optimized`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID AS
SELECT *
FROM `your-project.nytaxi.yellow_tripdata_2024`;
