# IMPORTS
from confluent_kafka import Producer
from Test_Files.test_main import read_config
import json
import time
import random
import threading
from global_vars import vehicleIDs

secure_random = random.SystemRandom()

conf = read_config()
conf["client.id"]="ccloud-python-client-40191c14-5a20-4de3-8731-d68c3afffd29"
conf["acks"]="all"
conf["message.timeout.ms"]=10000

producer = Producer(conf)

# Simulate sensor data from vehicles
def send_vehicle_sensor_data(vehicle_id, start_lat, start_long, lat_increment, long_increment):
    latitude = start_lat
    longitude = start_long

    while True:
        # Simulate vehicle sensor data
        temperature = secure_random.uniform(0.0, 10.0)  
        speed = secure_random.uniform(0.0, 70.0)
        radiation = secure_random.uniform(900.0, 1500.0)
        humidity = secure_random.uniform(20.0, 65.0)


        # Update latitude and longitude
        latitude += lat_increment
        longitude += long_increment

        # Handle boundary conditions
        if latitude > 90.0 or latitude < -90.0:
            lat_increment *= -1  # Reverse direction
        if longitude > 180.0 or longitude < -180.0:
            long_increment *= -1  # Reverse direction

        vehicle_data = {
            "vehicle_id": vehicle_id,
            "temperature": temperature, "humidity":humidity, "radiation": radiation,
            "speed": speed,
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        }

        print(f"Sending data from vehicle {vehicle_id}: {vehicle_data}")

        producer.produce('vehicle-sensor-data', key=str(vehicle_id), value=json.dumps(vehicle_data).encode('utf-8'))
        producer.flush()
        time.sleep(5)

# Initialize vehicles with starting positions and increments
vehicle_initials = [
    {
        "vehicle_id": vehicle_id,
        "start_lat": secure_random.uniform(-10.0, 10.0),  
        "start_long": secure_random.uniform(-10.0, 10.0),  
        "lat_increment": secure_random.uniform(0.001, 0.01),  
        "long_increment": secure_random.uniform(0.001, 0.01)  
    }
    for vehicle_id in vehicleIDs
]

# Create and start threads for each vehicle
threads = []
for vehicle in vehicle_initials:
    thread = threading.Thread(
        target=send_vehicle_sensor_data,
        args=(
            vehicle["vehicle_id"],
            vehicle["start_lat"],
            vehicle["start_long"],
            vehicle["lat_increment"],
            vehicle["long_increment"]
        )
    )
    thread.start()
    threads.append(thread)

# Join threads
for thread in threads:
    thread.join()
