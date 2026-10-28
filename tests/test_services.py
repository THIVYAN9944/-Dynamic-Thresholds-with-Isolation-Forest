"""
Unit Tests for CampusPulse Services (Localisation and Recommendations).

Validates:
- Multi-criteria weighted fault localisation algorithm.
- Prescriptive decision tree recommendation heuristics.
- Fault tolerance against malformed, sparse, and empty inputs.
"""

import sys
import os
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import localisation, recommendation


class TestLocalisationService:
    """Tests the campus degradation localisation service."""

    def test_empty_inputs_returns_none(self):
        """Verifies that empty datasets return None without errors."""
        assert localisation.locate_affected_area([], []) is None
        assert localisation.locate_affected_area(None, None) is None

    def test_single_location_metric_degradation(self):
        """Verifies that an isolated metric spike correctly identifies the affected location."""
        metrics = [
            {"location_id": 1, "latency_ms": 20.0, "packet_loss_percent": 0.0},
            {"location_id": 2, "latency_ms": 300.0, "packet_loss_percent": 12.0} # Breaches latency & packet loss
        ]
        affected = localisation.locate_affected_area(metrics, [])
        assert affected == 2

    def test_user_reports_weighting(self):
        """Verifies that high severity user reports influence localisation scoring."""
        user_reports = [
            {"location_id": 1, "severity": "Low"},
            {"location_id": 3, "severity": "High"} # High severity weighs +5.0
        ]
        affected = localisation.locate_affected_area([], user_reports)
        assert affected == 3

    def test_combined_metrics_and_crowdsourced_reports(self):
        """Verifies multi-criteria fusion when metrics and user reports correlate."""
        metrics = [
            {"location_id": 1, "latency_ms": 200.0}, # +2.0
            {"location_id": 2, "wifi_rssi": -92.0}   # +2.0
        ]
        user_reports = [
            {"location_id": 2, "severity": "Medium"} # +3.0 -> Total for loc 2 is 5.0
        ]
        affected = localisation.locate_affected_area(metrics, user_reports)
        assert affected == 2

    def test_malformed_records_tolerated(self):
        """Verifies error boundary filters out non-dictionary records and invalid values."""
        malformed_metrics = [
            "NOT_A_DICT",
            {"location_id": None},
            {"location_id": 1, "latency_ms": "NON_NUMERIC"},
            {"location_id": 4, "latency_ms": 250.0}
        ]
        affected = localisation.locate_affected_area(malformed_metrics, None)
        assert affected == 4


class TestRecommendationService:
    """Tests prescriptive recommendation heuristics."""

    def test_nominal_healthy_metrics(self):
        """No anomalies should return standard healthy confirmation."""
        rec = recommendation.generate_recommendation([], {})
        assert "within normal ranges" in rec

    def test_weak_wifi_capacity_overload(self):
        """Weak Wi-Fi with high client count recommends AP capacity expansion."""
        rec = recommendation.generate_recommendation(["Weak Wi-Fi"], {"connected_users": 65})
        assert "handling too many devices" in rec
        assert "additional access points" in rec

    def test_weak_wifi_rf_attenuation(self):
        """Weak Wi-Fi with normal client count recommends checking physical RF and AP hardware."""
        rec = recommendation.generate_recommendation(["Weak Wi-Fi"], {"connected_users": 15})
        assert "physical interference" in rec
        assert "check the physical device" in rec

    def test_network_latency_and_packet_loss(self):
        """Latency and packet loss recommend checking switch port and uplink infrastructure."""
        rec = recommendation.generate_recommendation(["High Latency", "Packet Loss"], {})
        assert "faulty switch or an overloaded uplink" in rec

    def test_isolated_application_slowdown(self):
        """Isolated app slowdown with healthy network attributes blame to upstream server."""
        rec = recommendation.generate_recommendation(["Application Slowdown"], {})
        assert "network appears healthy, but the application is responding slowly" in rec

    def test_cascading_application_slowdown(self):
        """App slowdown concurrent with network degradation notes cascading root cause."""
        rec = recommendation.generate_recommendation(["High Latency", "Application Slowdown"], {})
        assert "likely due to the ongoing network issues" in rec

    def test_multivariate_unusual_behavior(self):
        """Dynamic ML multivariate anomaly triggers baseline investigation advice."""
        rec = recommendation.generate_recommendation(["Unusual Network Behavior"], {})
        assert "Multivariate anomaly detected by dynamic baseline model" in rec

    def test_none_parameters_handled_safely(self):
        """Error boundary safely handles None arguments."""
        rec = recommendation.generate_recommendation(None, None)
        assert "within normal ranges" in rec
