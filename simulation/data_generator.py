import random
import time
import requests
from datetime import datetime

API_URL = "http://127.0.0.1:8000/api"

LOCATIONS = [
    {"name": "Classroom Block A", "latitude": 1.29, "longitude": 103.77},
    {"name": "Classroom Block B", "latitude": 1.291, "longitude": 103.772},
    {"name": "Hostel Block", "latitude": 1.292, "longitude": 103.775},
    {"name": "Laboratory", "latitude": 1.293, "longitude": 103.771},
    {"name": "Office", "latitude": 1.294, "longitude": 103.776},
    {"name": "Event Area", "latitude": 1.295, "longitude": 103.778},
]

def initialize_locations():
    try:
        existing = requests.get(f"{API_URL}/locations").json()
        if len(existing) == 0:
            for loc in LOCATIONS:
                requests.post(f"{API_URL}/locations", json=loc)
            print("Locations initialized.")
        else:
            print("Locations already exist.")
    except Exception as e:
        print(f"Error initializing locations: {e}")

def get_location_ids():
    try:
        locations = requests.get(f"{API_URL}/locations").json()
        return [loc["id"] for loc in locations]
    except:
        return []

def generate_normal_data(location_id):
    timestamp = datetime.utcnow().isoformat()
    
    probe_data = {
        "location_id": location_id,
        "latency_ms": random.uniform(10, 45),
        "packet_loss_percent": random.uniform(0, 1.5),
        "timestamp": timestamp
    }
    requests.post(f"{API_URL}/probe", json=probe_data)
    
    wifi_data = {
        "location_id": location_id,
        "wifi_rssi": random.uniform(-75, -50),
        "wifi_quality": random.uniform(80, 100),
        "connected_users": random.randint(10, 50),
        "timestamp": timestamp
    }
    requests.post(f"{API_URL}/wifi", json=wifi_data)
    
    app_data = {
        "location_id": location_id,
        "app_response_time_ms": random.uniform(50, 150),
        "app_status_code": 200,
        "timestamp": timestamp
    }
    requests.post(f"{API_URL}/application", json=app_data)

def simulate_background_traffic(duration_sec=60, interval_sec=5):
    initialize_locations()
    loc_ids = get_location_ids()
    if not loc_ids:
        print("No locations found, returning")
        return
        
    end_time = time.time() + duration_sec
    while time.time() < end_time:
        for loc_id in loc_ids:
            generate_normal_data(loc_id)
        time.sleep(interval_sec)

if __name__ == "__main__":
    simulate_background_traffic(10, 2)
