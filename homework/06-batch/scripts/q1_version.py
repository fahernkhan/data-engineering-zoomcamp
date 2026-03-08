# scripts/q1_version.py
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("hw6_q1") \
    .master("local[*]") \
    .getOrCreate()

print("Q1 — spark.version:", spark.version)
spark.stop()