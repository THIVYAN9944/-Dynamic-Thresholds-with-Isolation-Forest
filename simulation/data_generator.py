"""
CampusPulse Synthetic Telemetry Generator.

Emulates multi-vantage background network traffic across multiple campus buildings
(classrooms, hostels, laboratories, offices, event areas) at periodic intervals.
"""

import time
import random
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests

logger = logging.getLogger("campuspulse.generator")

API_URL = "http://127.0.0.1:8000/api"

# Default benchmark locations across campus
LOCATIONS: List[Dict[str, Any]] = [
    {"name": "Classroom Block A", "latitude": 1.2900, "longitude": 103.7700},
    {"name": "Classroom Block B", "latitude": 1.2910, "longitude": 103.7720},
    {"name": "Hostel Block", "latitude": 1.2920, "longitude": 103.7750},
    {"name": "Laboratory", "latitude": 1.2930, "longitude": 103.7710},
    {"name": "Office", "latitude": 1.2940, "longitude": 103.7760},
    {"name": "Event Area", "latitude": 1.2950, "longitude": 103.7780},
]


def initialize_locations() -> None:
    """
    Ensures standard campus locations exist in the database.
    Safe idempotent operation that avoids duplicating locations.
    """
    try:
        resp = requests.get(f"{API_URL}/locations", timeout=5)
        if resp.status_code == 200:
            existing = resp.json()
            existing_names = {loc["name"] for loc in existing}
            for loc in LOCATIONS:
                if loc["name"] not in existing_names:
                    requests.post(f"{API_URL}/locations", json=loc, timeout=5)
            logger.info("Campus locations initialized successfully.")
        else:
            logger.warning("Failed to fetch locations: status %s", resp.status_code)
    except requests.RequestException as exc:
        logger.warning("Backend API not reachable for initializing locations: %s", exc)


def get_location_ids() -> List[int]:
    """
    Fetches the list of active location IDs from the backend.
    
    Returns:
        List[int]: List of location IDs, or empty list if API unreachable.
    """
    try:
        resp = requests.get(f"{API_URL}/locations", timeout=5)
        if resp.status_code == 200:
            return [loc["id"] for loc in resp.json()]
    except requests.RequestException:
        pass
    return []


def generate_normal_data(location_id: int) -> None:
    """
    Generates and ingests a single healthy telemetry sample across all three streams:
    - Probe metrics: RTT 10-45ms, 0-1.5% packet loss
    - Wi-Fi metrics: -75 to -50 dBm RSSI, 80-100 quality score, 10-50 connected users
    - Application metrics: 50-150ms TTFB, HTTP 200 OK
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Ingest probe telemetry
    probe_payload = {
        "location_id": location_id,
        "latency_ms": round(random.uniform(10.0, 45.0), 2),
        "packet_loss_percent": round(random.uniform(0.0, 1.5), 2),
        "timestamp": timestamp
    }
    try:
        requests.post(f"{API_URL}/probe", json=probe_payload, timeout=5)
    except requests.RequestException as exc:
        logger.warning("Error posting probe telemetry: %s", exc)

    # 2. Ingest Wi-Fi telemetry
    wifi_payload = {
        "location_id": location_id,
        "wifi_rssi": round(random.uniform(-75.0, -50.0), 1),
        "wifi_quality": round(random.uniform(80.0, 100.0), 1),
        "connected_users": random.randint(10, 50),
        "timestamp": timestamp
    }
    try:
        requests.post(f"{API_URL}/wifi", json=wifi_payload, timeout=5)
    except requests.RequestException as exc:
        logger.warning("Error posting Wi-Fi telemetry: %s", exc)

    # 3. Ingest Application telemetry
    app_payload = {
        "location_id": location_id,
        "app_response_time_ms": round(random.uniform(50.0, 150.0), 2),
        "app_status_code": 200,
        "timestamp": timestamp
    }
    try:
        requests.post(f"{API_URL}/application", json=app_payload, timeout=5)
    except requests.RequestException as exc:
        logger.warning("Error posting application telemetry: %s", exc)


def simulate_background_traffic(duration_sec: int = 60, interval_sec: int = 5) -> None:
    """
    Generates background telemetry loops across all locations for a specified duration.
    """
    initialize_locations()
    loc_ids = get_location_ids()
    if not loc_ids:
        logger.warning("No locations available to simulate traffic.")
        return

    logger.info("Beginning traffic simulation across %d locations for %ds...", len(loc_ids), duration_sec)
    end_time = time.time() + duration_sec
    while time.time() < end_time:
        for loc_id in loc_ids:
            generate_normal_data(loc_id)
        time.sleep(interval_sec)
    logger.info("Simulation completed.")


if __name__ == "__main__":
    simulate_background_traffic(duration_sec=10, interval_sec=2)
