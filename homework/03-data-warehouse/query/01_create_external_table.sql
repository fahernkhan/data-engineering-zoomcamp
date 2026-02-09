CREATE OR REPLACE EXTERNAL TABLE
  `your-project.nytaxi.external_yellow_2024`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://your-bucket/yellow/2024/*.parquet']
);
