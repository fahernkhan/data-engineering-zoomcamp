SELECT DISTINCT VendorID
FROM `your-project.nytaxi.yellow_tripdata_optimized`
WHERE DATE(tpep_dropoff_datetime)
BETWEEN '2024-03-01' AND '2024-03-15';
