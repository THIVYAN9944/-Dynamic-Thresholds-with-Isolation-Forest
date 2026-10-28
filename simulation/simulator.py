"""
CampusPulse Failure Simulation Utility.

Provides programmatic injection routines for simulating intermittent campus network failures:
- High Latency: Simulates uplink congestion or bad routing (RTT 200-500ms).
- Packet Loss: Simulates duplex mismatches, bufferbloat, or dropped frames (10-25%).
- Weak Wi-Fi: Simulates RF attenuation, multipath fading, or low AP power (-95 to -85 dBm).
- Application Slowdown: Simulates backend database contention or thread starvation (800-2000ms TTFB).
"""

import random
import logging
from datetime import datetime, timezone
from typing import Optional
import requests

logger = logging.getLogger("campuspulse.simulation")

API_URL = "http://127.0.0.1:8000/api"


def _get_iso_utc() -> str:
    """Returns current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def inject_high_latency(location_id: int, duration_sec: int = 60) -> Optional[requests.Response]:
    """
    Injects anomalous high latency telemetry for a specific campus location.

    Baseline: 10-45ms RTT.
    Injected anomaly: 200-500ms RTT (threshold is 150ms).
    """
    probe_data = {
        "location_id": location_id,
        "latency_ms": round(random.uniform(200.0, 500.0), 2),
        "packet_loss_percent": round(random.uniform(0.0, 1.5), 2),
        "timestamp": _get_iso_utc()
    }
    try:
        resp = requests.post(f"{API_URL}/probe", json=probe_data, timeout=5)
        logger.info("Injected high latency for location %s: %s", location_id, resp.status_code)
        return resp
    except requests.RequestException as exc:
        logger.error("Failed to inject high latency: %s", exc)
        return None


def inject_packet_loss(location_id: int, duration_sec: int = 60) -> Optional[requests.Response]:
    """
    Injects anomalous packet drop telemetry.

    Baseline: 0-1.5% packet loss.
    Injected anomaly: 10-25% packet loss (threshold is 5.0%).
    """
    probe_data = {
        "location_id": location_id,
        "latency_ms": round(random.uniform(20.0, 50.0), 2),
        "packet_loss_percent": round(random.uniform(10.0, 25.0), 2),
        "timestamp": _get_iso_utc()
    }
    try:
        resp = requests.post(f"{API_URL}/probe", json=probe_data, timeout=5)
        logger.info("Injected packet loss for location %s: %s", location_id, resp.status_code)
        return resp
    except requests.RequestException as exc:
        logger.error("Failed to inject packet loss: %s", exc)
        return None


def inject_weak_wifi(location_id: int, duration_sec: int = 60) -> Optional[requests.Response]:
    """
    Injects anomalous weak Wi-Fi signal telemetry.

    Baseline: -75 to -50 dBm RSSI, 80-100 quality.
    Injected anomaly: -95 to -85 dBm RSSI (threshold is -80 dBm), 20-40 quality.
    """
    wifi_data = {
        "location_id": location_id,
        "wifi_rssi": round(random.uniform(-95.0, -85.0), 1),
        "wifi_quality": round(random.uniform(20.0, 40.0), 1),
        "connected_users": random.randint(10, 50),
        "timestamp": _get_iso_utc()
    }
    try:
        resp = requests.post(f"{API_URL}/wifi", json=wifi_data, timeout=5)
        logger.info("Injected weak Wi-Fi for location %s: %s", location_id, resp.status_code)
        return resp
    except requests.RequestException as exc:
        logger.error("Failed to inject weak Wi-Fi: %s", exc)
        return None


def inject_app_slowdown(location_id: int, duration_sec: int = 60) -> Optional[requests.Response]:
    """
    Injects anomalous application response latency.

    Baseline: 50-150ms HTTP TTFB.
    Injected anomaly: 800-2000ms HTTP TTFB (threshold is 500ms), HTTP 500 status code.
    """
    app_data = {
        "location_id": location_id,
        "app_response_time_ms": round(random.uniform(800.0, 2000.0), 2),
        "app_status_code": 500,
        "timestamp": _get_iso_utc()
    }
    try:
        resp = requests.post(f"{API_URL}/application", json=app_data, timeout=5)
        logger.info("Injected application slowdown for location %s: %s", location_id, resp.status_code)
        return resp
    except requests.RequestException as exc:
        logger.error("Failed to inject app slowdown: %s", exc)
        return None
