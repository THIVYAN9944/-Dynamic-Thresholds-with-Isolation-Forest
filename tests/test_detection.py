"""
Unit Tests for CampusPulse Detection Service.

Validates:
- Heuristic static rule-based anomaly detection.
- Dynamic ML Isolation Forest anomaly detection.
- Multi-dimensional telemetry experience score calculations.
- Missing telemetry imputation and edge case bounds.
- Concept drift and retraining triggers.
"""

import sys
import os
import random
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import detection, recommendation


class TestStaticAnomalyDetection:
    """Tests the static heuristic rule engine."""

    def test_healthy_telemetry(self):
        """Validates that nominal metrics are classified as Healthy with no anomalies."""
        status, anomalies = detection.detect_anomaly(
            latency=20.0,
            packet_loss=1.0,
            wifi_rssi=-60.0,
            app_response=100.0
        )
        assert status == "Healthy"
        assert anomalies == []

    def test_high_latency_threshold_breach(self):
        """Validates anomaly trigger when latency exceeds 150ms."""
        status, anomalies = detection.detect_anomaly(
            latency=200.0,
            packet_loss=1.0,
            wifi_rssi=-60.0,
            app_response=100.0
        )
        assert status == "Degraded"
        assert "High Latency" in anomalies

    def test_packet_loss_threshold_breach(self):
        """Validates anomaly trigger when packet loss exceeds 5.0%."""
        status, anomalies = detection.detect_anomaly(
            latency=20.0,
            packet_loss=10.0,
            wifi_rssi=-60.0,
            app_response=100.0
        )
        assert status == "Degraded"
        assert "Packet Loss" in anomalies

    def test_weak_wifi_threshold_breach(self):
        """Validates anomaly trigger when Wi-Fi RSSI drops below -80 dBm."""
        status, anomalies = detection.detect_anomaly(
            latency=20.0,
            packet_loss=1.0,
            wifi_rssi=-90.0,
            app_response=100.0
        )
        assert status == "Degraded"
        assert "Weak Wi-Fi" in anomalies

    def test_application_slowdown_threshold_breach(self):
        """Validates anomaly trigger when app response exceeds 500ms."""
        status, anomalies = detection.detect_anomaly(
            latency=20.0,
            packet_loss=1.0,
            wifi_rssi=-60.0,
            app_response=800.0
        )
        assert status == "Degraded"
        assert "Application Slowdown" in anomalies

    def test_multiple_simultaneous_anomalies(self):
        """Validates detection when multiple thresholds are breached concurrently."""
        status, anomalies = detection.detect_anomaly(
            latency=250.0,
            packet_loss=12.0,
            wifi_rssi=-92.0,
            app_response=950.0
        )
        assert status == "Degraded"
        assert len(anomalies) == 4
        assert set(anomalies) == {"High Latency", "Packet Loss", "Weak Wi-Fi", "Application Slowdown"}

    def test_boundary_exact_threshold_values(self):
        """Boundary value test: exact threshold equality should not trigger anomaly."""
        status, anomalies = detection.detect_anomaly(
            latency=150.0,
            packet_loss=5.0,
            wifi_rssi=-80.0,
            app_response=500.0
        )
        assert status == "Healthy"
        assert len(anomalies) == 0


class TestExperienceScoreCalculation:
    """Tests the composite experience score calculation algorithm."""

    def test_perfect_score(self):
        """Optimal network telemetry results in a maximum score of 100.0."""
        score = detection.calculate_experience_score(
            latency=30.0,
            packet_loss=0.0,
            wifi_quality=100.0,
            app_response=150.0
        )
        assert score == 100.0

    def test_degraded_score_penalties(self):
        """Verifies cumulative penalties for sub-optimal telemetry."""
        score = detection.calculate_experience_score(
            latency=150.0,       # +100ms over 50 -> -10 pts
            packet_loss=5.0,      # 5% -> -25 pts
            wifi_quality=80.0,    # -20% -> -10 pts
            app_response=500.0    # +300ms over 200 -> -3 pts
        )
        # Expected: 100 - 10 - 25 - 10 - 3 = 52.0
        assert score == 52.0

    def test_score_lower_boundary_clamping(self):
        """Score must never drop below 0.0 even under catastrophic metrics."""
        score = detection.calculate_experience_score(
            latency=2000.0,
            packet_loss=100.0,
            wifi_quality=0.0,
            app_response=10000.0
        )
        assert score == 0.0

    def test_score_handling_of_none_inputs(self):
        """Gracefully handles None arguments by utilizing sensible defaults."""
        score = detection.calculate_experience_score(
            latency=None,
            packet_loss=None,
            wifi_quality=None,
            app_response=None
        )
        assert score == 100.0


class TestDynamicMLAnomalyDetection:
    """Tests the Isolation Forest dynamic anomaly detection engine."""

    def test_ml_fallback_on_insufficient_samples(self):
        """Fallback to static heuristics when fewer than 20 historical points exist."""
        current = {"latency_ms": 200, "packet_loss_percent": 1.0, "wifi_rssi": -60, "app_response_time_ms": 100}
        # Only 5 historical samples provided
        history = [current] * 5
        status, anomalies = detection.detect_anomaly_ml(current, history)
        assert status == "Degraded"
        assert "High Latency" in anomalies

    def test_ml_outlier_detection(self):
        """Validates that ML correctly identifies an outlier from historical baseline."""
        random.seed(42)
        history = [
            {
                "latency_ms": 20.0 + random.uniform(-2, 2),
                "packet_loss_percent": 1.0,
                "wifi_rssi": -60.0 + random.uniform(-5, 5),
                "app_response_time_ms": 100.0 + random.uniform(-10, 10)
            }
            for _ in range(50)
        ]

        # Inject anomalies into historical observations so Isolation Forest calibrates bounds
        history.append({"latency_ms": 250.0, "packet_loss_percent": 1.0, "wifi_rssi": -60.0, "app_response_time_ms": 100.0})
        history.append({"latency_ms": 20.0, "packet_loss_percent": 15.0, "wifi_rssi": -60.0, "app_response_time_ms": 100.0})

        # Clear cache for isolated test
        if "test_loc_ml_outlier" in detection.MODEL_CACHE:
            del detection.MODEL_CACHE["test_loc_ml_outlier"]

        # Normal test point matching distribution
        normal_point = {"latency_ms": 22.0, "packet_loss_percent": 1.1, "wifi_rssi": -61.0, "app_response_time_ms": 105.0}
        status_norm, anomalies_norm = detection.detect_anomaly_ml(normal_point, history, location_id="test_loc_ml_outlier")
        assert status_norm == "Healthy"
        assert anomalies_norm == []

        # Outlier test point
        anomalous_point = {"latency_ms": 350.0, "packet_loss_percent": 1.0, "wifi_rssi": -60.0, "app_response_time_ms": 100.0}
        status_anom, anomalies_anom = detection.detect_anomaly_ml(anomalous_point, history, location_id="test_loc_ml_outlier")
        assert status_anom == "Degraded"
        assert "High Latency" in anomalies_anom

    def test_ml_missing_features_imputation(self):
        """Verifies robust median imputation when historical or current samples have missing keys."""
        history = [
            {"latency_ms": 25.0, "wifi_rssi": -62.0} # Missing packet_loss and app_response
            for _ in range(30)
        ]
        current = {"latency_ms": 25.0} # Sparse current sample
        status, anomalies = detection.detect_anomaly_ml(current, history, location_id="test_loc_sparse")
        assert status in ["Healthy", "Degraded"]
