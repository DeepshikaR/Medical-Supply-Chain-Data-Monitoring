from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, lit, current_timestamp, when, udf, to_json, struct, rand, ceil
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, TimestampType, FloatType
from global_vars import warehouse_stock
from tensorflow.keras.models import load_model
from keras.losses import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from Test_Files.test_lstm import last_known
import numpy as np
import json
import os


# Initialize Spark session
spark = SparkSession.builder \
    .appName("warehouseUpdates") \
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
    .option("subscribe", "factory-updates") \
    .option("startingOffsets", "earliest") \
    .load()


# Deserialize JSON data
schema = StructType([
    StructField("factory_id", IntegerType(), True),
    StructField("vaccine_id_1", IntegerType(), True),
    StructField("quantity_id_1", IntegerType(), True),
    StructField("batch_id_1", IntegerType(), True),
    StructField("vaccine_id_2", IntegerType(), True),
    StructField("quantity_id_2", IntegerType(), True),
    StructField("batch_id_2", IntegerType(), True),
    StructField("timestamp", StringType(), True)
])

parsed_df = kafka_df.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")

# Function to check for existing records
@udf(IntegerType())
def update_quantity(warehouse_id, vaccine_id, quantity):
    warehouse_stock[warehouse_id] += quantity
    return warehouse_stock[warehouse_id]


# Transform and update the warehouse data
updates_df = parsed_df.select(
    col("vaccine_id_1").alias("warehouse_id"),
    col("vaccine_id_1").alias("vaccine_id"),
    update_quantity(col("vaccine_id_1"), col("vaccine_id_1"), col("quantity_id_1")).alias("quantity"),
    col("timestamp").alias("timestamp")
).union(parsed_df.select(
    col("vaccine_id_2").alias("warehouse_id"),
    col("vaccine_id_2").alias("vaccine_id"),
    update_quantity(col("vaccine_id_2"), col("vaccine_id_2"), col("quantity_id_2")).alias("quantity"),
    col("timestamp").alias("timestamp")
))


# Serialize the output as JSON
output_df = updates_df.select(to_json(struct("*")).alias("value"))


# Write updates to the warehouse 
query = output_df.writeStream \
    .format("kafka") \
    .options(**kafka_security_config) \
    .option("topic", "inventory-updates") \
    .option("checkpointLocation", "/tmp/spark_warehouse_checkpoints") \
    .start()


autoencoder = load_model('./ML_Models/inventory_anomaly.h5',custom_objects={'mse': mean_squared_error})
scaler = MinMaxScaler()
lstm_Model = load_model('./ML_Models/demand_lstm.h5',custom_objects={'mse': mean_squared_error})

# Function to detect inventory anomalies
@udf(FloatType())
def detect_inventory_anomaly(inventory_level):
    # print(f"Inventory level received: {inventory_level}")
    inventory_level = scaler.fit_transform([[inventory_level]])  # Normalize
    reconstruction = autoencoder.predict(inventory_level)
    error = np.abs(reconstruction - inventory_level)
    return float(error)


# Function to predict demand using lstm
@udf(FloatType())
def predict_demand(inventory_level):
    delivery_time = inventory_level/15
    last_known[-1, 1] = scaler.transform([[0, inventory_level, delivery_time, 0]])[0, 1]  
    last_known[-1, 2] = scaler.transform([[0, inventory_level, delivery_time, 0]])[0, 2]    
    next_day = model.predict(last_known.reshape(1, 7, 4), verbose=0)
    dummy = np.zeros((1, scaler.n_features_in_))
    dummy[0, 0] = next_day[0, 0]
    predicted_demand = scaler.inverse_transform(dummy)[0, 0]
    return float(predicted_demand)



df_spark = updates_df \
    .withColumn("Anomaly_Score", detect_inventory_anomaly(updates_df["quantity"]))\
    .withColumn("Predicted_Demand", predict_demand(updates_df["quantity"]))


# Serialize the output as JSON
output_df_1 = df_spark.select(to_json(struct("*")).alias("value"))


query1 = output_df_1.writeStream \
    .format("kafka") \
    .options(**kafka_security_config) \
    .option("topic", "inventory-predictions") \
    .option("checkpointLocation", "/tmp/spark_i_preds_checkpoint") \
    .start()


query.awaitTermination()
query1.awaitTermination()

