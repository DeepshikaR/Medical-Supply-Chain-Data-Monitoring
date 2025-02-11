from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, to_json, struct, from_json
from pyspark.sql.types import StringType, DoubleType, LongType, MapType, StructType, StructField


# Initialize Spark session
spark = SparkSession.builder \
    .appName("SensorViolations") \
    .getOrCreate()


# Kafka configuration for Confluent Cloud
kafka_bootstrap_servers = "pkc-XXXX.us-east1.gcp.confluent.cloud:9092"
kafka_security_config = {
    "kafka.bootstrap.servers": kafka_bootstrap_servers,
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.jaas.config": "org.apache.kafka.common.security.plain.PlainLoginModule required username='USERNAME' password='PASSWORD';"
}


# Read from Kafka Broker
kafka_df = spark.readStream \
    .format("kafka") \
    .options(**kafka_security_config) \
    .option("subscribe", "vehicle-sensor-data") \
    .option("startingOffsets", "earliest") \
    .load()


# Deserialize JSON data
schema = StructType([
    StructField("vehicle_id", StringType(), True),
    StructField("temperature", DoubleType(), True),
    StructField("humidity", DoubleType(), True),
    StructField("radiation", DoubleType(), True),
    StructField("speed", DoubleType(), True),
    StructField("location", MapType(StringType(), DoubleType()), True),
    StructField("timestamp", StringType(), True)
])

parsed_df = kafka_df.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")

# Add violation flag
flagged_df = parsed_df.withColumn(
    "violation_flag",
    when((col("temperature") < 2) | (col("temperature") > 8) |
         (col("humidity") >= 55) | (col("radiation") >= 1380), True).otherwise(False)
)

# Serialize the output as JSON
output_df = flagged_df.select(to_json(struct("*")).alias("value"))

# Write flagged data to Kafka
query = output_df.writeStream \
    .format("kafka") \
    .options(**kafka_security_config) \
    .option("topic", "flagged-sensor-data") \
    .option("checkpointLocation", "/tmp/spark_sensor_checkpoint") \
    .start()

query.awaitTermination()

