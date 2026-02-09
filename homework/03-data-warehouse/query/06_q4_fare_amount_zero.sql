SELECT COUNT(*) AS zero_fare_trips
FROM `your-project.nytaxi.yellow_tripdata_2024`
WHERE fare_amount = 0;
