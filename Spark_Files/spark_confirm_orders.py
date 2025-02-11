from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, lit, current_timestamp, when, udf, to_json, struct
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, TimestampType
from global_vars import time_map, warehouse_stock
from datetime import datetime, timedelta
from tensorflow.keras.models import load_model
from keras.losses import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
import json
import os


# Initialize Spark session
spark = SparkSession.builder \
    .appName("confirmOrders") \
    .getOrCreate()

# Kafka configuration for Confluent Cloud
kafka_bootstrap_servers = "pkc-XXXX.us-east1.gcp.confluent.cloud:9092"
kafka_security_config = {
    "kafka.bootstrap.servers": kafka_bootstrap_servers,
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.jaas.config": "org.apache.kafka.common.security.plain.PlainLoginModule required username='USERNAME' password='PASSWORD';"
}

# Read from Kafka
kafka_df = spark.readStream \
    .format("kafka") \
    .options(**kafka_security_config) \
    .option("subscribe", "customer-orders") \
    .option("startingOffsets", "earliest") \
    .load()

# Deserialize JSON data
schema = StructType([
    StructField("hospital_id", IntegerType(), True),
    StructField("vaccine_id", IntegerType(), True),
    StructField("quantity", IntegerType(), True),
    StructField("timestamp", StringType(), True),
    StructField("expected_delivery", StringType(), True),
])

parsed_df = kafka_df.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")


@udf(StringType())
def calc_estimated_delivery(hospital_id, vaccine_id,timestamp):
    delivery_time = time_map[vaccine_id][hospital_id]
    timestamp = datetime.strptime(timestamp,"%Y-%m-%d %H:%M:%S")
    estimated_time = timestamp + timedelta(hours=delivery_time)
    return estimated_time.strftime("%Y-%m-%d %H:%M:%S")


@udf(IntegerType())
def update_quantity(warehouse_id, quantity):
    stock = warehouse_stock[warehouse_id]
    if stock != 0:
        warehouse_stock[warehouse_id]-= quantity
    return warehouse_stock[warehouse_id]


autoencoder = load_model('./ML_Models/delivery_anomaly.h5',custom_objects={'mse': mean_squared_error})    
scaler = MinMaxScaler()

@udf(FloatType())
def detect_inventory_anomaly(hospital_id, vaccine_id, quantity, timestamp):
    # print(f"Inventory level received: {inventory_level}")
    delivery_time = time_map[vaccine_id][hospital_id]
    distance = delivery_time
    timestamp = datetime.strptime(timestamp,"%Y-%m-%d %H:%M:%S")
    time_order = timestamp.hour
    delivery_data = [[delivery_time, distance, quantity, time_order]]
    delivery_details = scaler.fit_transform(delivery_data)  # Normalize    
    reconstruction = autoencoder.predict(delivery_details)
    error = np.abs(reconstruction - delivery_details)
    # print(f"ERROR: {error}")
    return float(error)


# Add estimated delivery date
new_df = parsed_df\
    .withColumn("estimated_delivery",calc_estimated_delivery(col("hospital_id"),col("vaccine_id"),col("timestamp"))) \
    .withColumn("delivery_anomaly", detect_inventory_anomaly(col("hospital_id"),col("vaccine_id"),col("quantity"),col("timestamp")))

output_df = new_df.select(to_json(struct("*")).alias("value"))


query = output_df.writeStream \
    .format("kafka") \
    .options(**kafka_security_config) \
    .option("topic", "confirmed-orders") \
    .option("checkpointLocation", "/tmp/spark_c_orders_checkpoint") \
    .start()


warehouse_updates_df = parsed_df.select(
    col("vaccine_id").alias("warehouse_id"),
    col("vaccine_id").alias("vaccine_id"),
    update_quantity(col("vaccine_id"), col("quantity")).alias("quantity"),
    col("timestamp").alias("timestamp")
)

# Serialize the output as JSON
w_output_df = warehouse_updates_df.select(to_json(struct("*")).alias("value"))


# Write updates to the warehouse JSON file
query_1 = w_output_df.writeStream \
   .format("kafka") \
   .options(**kafka_security_config) \
   .option("topic", "inventory-updates") \
  .option("checkpointLocation", "/tmp/spark_checkpoint") \
   .start()

query.awaitTermination()
query_1.awaitTermination()
