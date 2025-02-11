# IMPORTS
from confluent_kafka import Producer
from Test_Files.test_main import read_config
import json
import time
import random
from datetime import datetime, timedelta
from global_vars import hospitalIDs, vaccineIDs

secure_random = random.SystemRandom()

conf = read_config()
conf["client.id"]="ccloud-python-client-40191c14-5a20-4de3-8731-d68c3afffd29"
conf["acks"]="all"
conf["message.timeout.ms"]=10000

# Create a Kafka producer
producer = Producer(conf)

# Define function to generate customer orders data
def generate_customer_order():
    hospital_id = secure_random.choice(hospitalIDs)
    vaccine_id = secure_random.choice(vaccineIDs)
    quantity = secure_random.randint(10, 30)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    current_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    expected_delivery = (current_time + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
	
    
    return {
        'hospital_id': hospital_id,
        'vaccine_id': vaccine_id,
        'quantity': quantity,
        'timestamp': timestamp,
        'expected_delivery': expected_delivery
    }

# Produce messages to the Kafka topic 'customer-orders'
topic_name = 'customer-orders'

# print("Producing customer order data to Kafka topic...")

try:
    while True:
        # Generate a random customer order
        order = generate_customer_order()

        # Send the order to the Kafka topic
        producer.produce(topic_name, key=str(order['hospital_id']),value=json.dumps(order).encode('utf-8'))
        producer.flush()

        print(f"Sent order: {order}")
        time.sleep(15)

except KeyboardInterrupt:
    print("Stopped producing messages.")
finally:
    producer.close()
