from pyspark.sql import SparkSession
from pyspark.sql.functions import col

spark = (
    SparkSession.builder
    .appName("minimal-airflow-pyspark")
    .getOrCreate()
)

data = [
    ("Dylan", 1),
    ("Airflow", 2),
    ("Spark", 3),
]

df = spark.createDataFrame(data, ["name", "value"])

result = df.withColumn("value_x10", col("value") * 10)

result.show()

spark.stop()