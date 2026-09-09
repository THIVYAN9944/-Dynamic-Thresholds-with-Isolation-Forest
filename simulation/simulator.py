import requests
import random
from datetime import datetime

API_URL = "http://127.0.0.1:8000/api"

def inject_high_latency(location_id, duration_sec=60):
    timestamp = datetime.utcnow().isoformat()
    probe_data = {
        "location_id": location_id,
        "latency_ms": random.uniform(200, 500), # Threshold is 150
        "packet_loss_percent": random.uniform(0, 1.5),
        "timestamp": timestamp
    }
    requests.post(f"{API_URL}/probe", json=probe_data)

def inject_packet_loss(location_id, duration_sec=60):
    timestamp = datetime.utcnow().isoformat()
    probe_data = {
        "location_id": location_id,
        "latency_ms": random.uniform(20, 50),
        "packet_loss_percent": random.uniform(10, 25), # Threshold is 5.0
        "timestamp": timestamp
    }
    requests.post(f"{API_URL}/probe", json=probe_data)

def inject_weak_wifi(location_id, duration_sec=60):
    timestamp = datetime.utcnow().isoformat()
    wifi_data = {
        "location_id": location_id,
        "wifi_rssi": random.uniform(-95, -85), # Threshold is -80
        "wifi_quality": random.uniform(20, 40),
        "connected_users": random.randint(10, 50),
        "timestamp": timestamp
    }
    requests.post(f"{API_URL}/wifi", json=wifi_data)

def inject_app_slowdown(location_id, duration_sec=60):
    timestamp = datetime.utcnow().isoformat()
    app_data = {
        "location_id": location_id,
        "app_response_time_ms": random.uniform(800, 2000), # Threshold is 500
        "app_status_code": 500,
        "timestamp": timestamp
    }
    requests.post(f"{API_URL}/application", json=app_data)
