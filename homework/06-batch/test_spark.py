import pyspark
from pyspark.sql import SparkSession
import os


spark = SparkSession.builder \
    .master("local[*]") \
    .appName("test") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")
print(f"Spark version: {spark.version}")

df = spark.range(10)
df.show()
print(os.environ.get("SPARK_HOME"))


spark.stop()