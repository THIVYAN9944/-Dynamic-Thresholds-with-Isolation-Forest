"""
CampusPulse Anomaly Localisation Service.

Determines the most degraded geographic zone or campus building by synthesizing
real-time automated telemetry metrics with subjective crowdsourced user reports
through a weighted multi-criteria ranking algorithm.
"""

from collections import defaultdict
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("campuspulse.localisation")

# Telemetry penalty weights
SEVERITY_WEIGHTS = {
    "latency_excess": 2.0,      # Weight for latency > 150ms
    "packet_loss_excess": 3.0,  # Weight for packet loss > 5%
    "weak_wifi": 2.0,           # Weight for RSSI < -80 dBm
    "app_slowdown": 1.0         # Weight for TTFB > 500ms
}

# User ticket urgency weights
USER_REPORT_WEIGHTS = {
    "High": 5.0,
    "Medium": 3.0,
    "Low": 1.0
}


def locate_affected_area(
    metrics_data: Optional[List[Dict[str, Any]]],
    user_reports: Optional[List[Dict[str, Any]]]
) -> Optional[int]:
    """
    Identifies the most critically degraded campus location ID.

    Error Boundaries:
    - Gracefully handles empty, None, or malformed inputs without raising uncaught exceptions.
    - Sanitizes missing or non-numeric metrics using fallback zero defaults.
    - Returns None if both datasets are empty or no locations exhibit degradation.

    Scoring Methodology:
    Each location accumulates penalty points:
    - Automated Telemetry:
        * Latency > 150ms adds +2.0
        * Packet loss > 5.0% adds +3.0
        * Wi-Fi RSSI < -80 dBm adds +2.0
        * App TTFB > 500ms adds +1.0
    - User Reports:
        * High severity adds +5.0
        * Medium severity adds +3.0
        * Low severity adds +1.0

    Args:
        metrics_data: List of telemetry dictionaries containing 'location_id' and metrics.
        user_reports: List of crowdsourced report dictionaries with 'location_id' and 'severity'.

    Returns:
        Optional[int]: Location ID with the highest cumulative degradation score,
                       or None if no anomalies are active.
    """
    location_scores: Dict[int, float] = defaultdict(float)

    # 1. Process automated telemetry streams
    if metrics_data:
        for data in metrics_data:
            if not isinstance(data, dict):
                continue
            loc_id = data.get("location_id")
            if loc_id is None:
                continue

            try:
                latency = float(data.get("latency_ms") or 0.0)
                packet_loss = float(data.get("packet_loss_percent") or 0.0)
                wifi_rssi = float(data.get("wifi_rssi") or 0.0)
                app_response = float(data.get("app_response_time_ms") or 0.0)

                if latency > 150.0:
                    location_scores[loc_id] += SEVERITY_WEIGHTS["latency_excess"]
                if packet_loss > 5.0:
                    location_scores[loc_id] += SEVERITY_WEIGHTS["packet_loss_excess"]
                if -120.0 <= wifi_rssi < -80.0:
                    location_scores[loc_id] += SEVERITY_WEIGHTS["weak_wifi"]
                if app_response > 500.0:
                    location_scores[loc_id] += SEVERITY_WEIGHTS["app_slowdown"]
            except (ValueError, TypeError) as err:
                logger.warning("Skipping malformed metric record for location %s: %s", loc_id, err)
                continue

    # 2. Process crowdsourced user feedback
    if user_reports:
        for report in user_reports:
            if not isinstance(report, dict):
                continue
            loc_id = report.get("location_id")
            if loc_id is None:
                continue

            severity = str(report.get("severity", "Low")).capitalize()
            weight = USER_REPORT_WEIGHTS.get(severity, USER_REPORT_WEIGHTS["Low"])
            location_scores[loc_id] += weight

    if not location_scores:
        return None

    # Determine location with the maximum cumulative degradation score
    most_affected = max(location_scores, key=lambda k: location_scores[k])
    return most_affected
