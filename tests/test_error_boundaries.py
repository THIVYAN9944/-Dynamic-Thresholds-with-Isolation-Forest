"""
Error Boundaries and Fault Tolerance Test Suite.

Explicitly tests system resiliency across:
1. HTTP 404 Error Boundaries: Rejecting telemetry for non-existent locations.
2. Pydantic HTTP 422 Validation Error Boundaries: Enforcing schema constraints on out-of-range metrics.
3. Machine Learning Error Boundaries: Graceful handling and recovery from corrupted model files.
4. Runtime Inference Fallback Boundaries: Transparent fallback to heuristic rules upon inference errors.
5. Numerical Score Clamping Boundaries: Bounding values safely between 0.0 and 100.0.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.database import get_db, Base
from backend.models import Location
from services import detection

# Dedicated test SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    loc = Location(name="Boundary Test Location")
    db.add(loc)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


class TestHTTP404ErrorBoundaries:
    """Verifies that referencing non-existent location IDs returns HTTP 404 instead of crashing."""

    def test_probe_nonexistent_location(self):
        resp = client.post("/api/probe", json={"location_id": 9999, "latency_ms": 20.0, "packet_loss_percent": 0.0})
        assert resp.status_code == 404
        assert "does not exist" in resp.json()["detail"]

    def test_wifi_nonexistent_location(self):
        resp = client.post("/api/wifi", json={"location_id": 9999, "wifi_rssi": -60.0, "wifi_quality": 85.0, "connected_users": 10})
        assert resp.status_code == 404
        assert "does not exist" in resp.json()["detail"]

    def test_application_nonexistent_location(self):
        resp = client.post("/api/application", json={"location_id": 9999, "app_response_time_ms": 100.0, "app_status_code": 200})
        assert resp.status_code == 404
        assert "does not exist" in resp.json()["detail"]

    def test_user_report_nonexistent_location(self):
        resp = client.post("/api/report", json={"location_id": 9999, "issue_type": "Lag", "severity": "Medium", "description": "High ping"})
        assert resp.status_code == 404
        assert "does not exist" in resp.json()["detail"]

    def test_incident_nonexistent_location(self):
        payload = {
            "location_id": 9999,
            "incident_type": "Packet Loss",
            "severity": "Degraded",
            "status": "Active",
            "start_time": "2026-10-28T10:00:00Z"
        }
        resp = client.post("/api/incidents", json=payload)
        assert resp.status_code == 404
        assert "does not exist" in resp.json()["detail"]


class TestHTTP422InputValidationBoundaries:
    """Verifies that out-of-range metrics trigger HTTP 422 Unprocessable Entity."""

    def test_probe_negative_latency_rejected(self):
        resp = client.post("/api/probe", json={"location_id": 1, "latency_ms": -10.0, "packet_loss_percent": 0.0})
        assert resp.status_code == 422

    def test_probe_excessive_packet_loss_rejected(self):
        resp = client.post("/api/probe", json={"location_id": 1, "latency_ms": 20.0, "packet_loss_percent": 150.0})
        assert resp.status_code == 422

    def test_wifi_out_of_bound_rssi_rejected(self):
        resp = client.post("/api/wifi", json={"location_id": 1, "wifi_rssi": -150.0, "wifi_quality": 80.0, "connected_users": 5})
        assert resp.status_code == 422

    def test_wifi_positive_rssi_rejected(self):
        resp = client.post("/api/wifi", json={"location_id": 1, "wifi_rssi": 10.0, "wifi_quality": 80.0, "connected_users": 5})
        assert resp.status_code == 422

    def test_wifi_negative_connected_users_rejected(self):
        resp = client.post("/api/wifi", json={"location_id": 1, "wifi_rssi": -65.0, "wifi_quality": 80.0, "connected_users": -3})
        assert resp.status_code == 422

    def test_application_negative_response_time_rejected(self):
        resp = client.post("/api/application", json={"location_id": 1, "app_response_time_ms": -50.0, "app_status_code": 200})
        assert resp.status_code == 422

    def test_application_invalid_status_code_rejected(self):
        resp = client.post("/api/application", json={"location_id": 1, "app_response_time_ms": 100.0, "app_status_code": 999})
        assert resp.status_code == 422

    def test_user_report_invalid_severity_rejected(self):
        resp = client.post("/api/report", json={"location_id": 1, "issue_type": "Slow", "severity": "Catastrophic", "description": ""})
        assert resp.status_code == 422


class TestMachineLearningErrorBoundaries:
    """Verifies fault tolerance and graceful degradation in the ML pipeline."""

    def test_corrupted_model_file_recovery(self, tmp_path):
        """Verifies that a corrupted joblib file does not crash inference and is safely recovered."""
        loc_id = "test_corrupt_boundary"
        model_path = os.path.join(detection.MODEL_DIR, f"iforest_{loc_id}.pkl")

        # Intentionally write garbage bytes to simulate corrupted file on disk
        with open(model_path, "wb") as f:
            f.write(b"CORRUPTED_NON_JOBLIB_DATA_GARBAGE_BYTES")

        # Clear memory cache to force reading from disk
        if loc_id in detection.MODEL_CACHE:
            del detection.MODEL_CACHE[loc_id]

        history = [
            {"latency_ms": 20.0, "packet_loss_percent": 0.5, "wifi_rssi": -60.0, "app_response_time_ms": 100.0}
            for _ in range(25)
        ]
        current = {"latency_ms": 20.0, "packet_loss_percent": 0.5, "wifi_rssi": -60.0, "app_response_time_ms": 100.0}

        # Must execute without raising unhandled exception
        status, anomalies = detection.detect_anomaly_ml(current, history, location_id=loc_id)
        assert status in ["Healthy", "Degraded"]

        # Clean up
        if os.path.exists(model_path):
            os.remove(model_path)
        if loc_id in detection.MODEL_CACHE:
            del detection.MODEL_CACHE[loc_id]

    def test_ml_matrix_exception_fallback_to_heuristic(self):
        """Verifies that passing completely unparseable structure falls back to static rules."""
        # Current metrics is completely empty
        status, anomalies = detection.detect_anomaly_ml({}, [], location_id="empty_test")
        assert status == "Healthy"
        assert anomalies == []


class TestScoreClampingBoundary:
    """Verifies numeric clamping boundaries on experience score computation."""

    def test_extreme_negative_score_clamped_to_zero(self):
        score = detection.calculate_experience_score(
            latency=50000.0,
            packet_loss=100.0,
            wifi_quality=0.0,
            app_response=100000.0
        )
        assert score == 0.0

    def test_extreme_over_optimal_score_capped_at_hundred(self):
        score = detection.calculate_experience_score(
            latency=0.0,
            packet_loss=0.0,
            wifi_quality=100.0,
            app_response=10.0
        )
        assert score == 100.0
