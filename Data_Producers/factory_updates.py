# IMPORTS
from confluent_kafka import Producer
from Test_Files.test_main import read_config
import json
import time
import random
import threading
from global_vars import warehouseIDs, vaccineIDs, factoryIDs

secure_random =  random.SystemRandom()

conf = read_config()
conf["client.id"]="ccloud-python-client-40191c14-5a20-4de3-8731-d68c3afffd29"
conf["acks"]="all"
conf["message.timeout.ms"]=10000

# Create a Kafka producer
producer = Producer(conf)

# Define a function to generate factory update data
def send_factory_update(id, vaccine1, vaccine2, batch1, batch2):
    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        quantity_1 = secure_random.randint(50, 100)
        quantity_2 = secure_random.randint(50, 100)

        vaccine1 = secure_random.choice(vaccineIDs)
        vaccine2 = secure_random.choice(vaccineIDs)

        batch1 += secure_random.randint(1, 5)
        batch2 += secure_random.randint(1, 5)

        factory_data = {
            "factory_id": id,
            "vaccine_id_1": vaccine1,
            "quantity_id_1": quantity_1,
            "batch_id_1": batch1,
            "vaccine_id_2": vaccine2,
            "quantity_id_2": quantity_2,
            "batch_id_2": batch2,
            "timestamp": timestamp
        }

        # print(f"Sending data from factory {id}: {factory_data}")

        producer.produce('factory-updates', key=str(id), value=json.dumps(factory_data).encode('utf-8'))
        producer.flush()
        time.sleep(20)

# Initialize data
factory_inits = [
    {
        "factory_id": factory_id,
        "vaccine_id_1": secure_random.choice(vaccineIDs), 
        "vaccine_id_2": secure_random.choice(vaccineIDs),  
        "batch_id_1": secure_random.randint(1000, 1010),
        "batch_id_2": secure_random.randint(2000, 2010)
    }
    for factory_id in factoryIDs 
]


# Create and start threads for each factory
threads = []
for factory in factory_inits:
    thread = threading.Thread(
        target=send_factory_update,
        args=(
            factory["factory_id"],
            factory["vaccine_id_1"],
            factory["vaccine_id_2"],
            factory["batch_id_1"],
            factory["batch_id_2"]
        )
    )
    thread.start()
    threads.append(thread)

# Join threads 
for thread in threads:
    thread.join()
