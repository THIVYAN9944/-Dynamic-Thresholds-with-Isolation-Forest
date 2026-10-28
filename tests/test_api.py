"""
Unit and Integration Tests for CampusPulse REST API.

Tests the full lifecycle of API endpoints:
- Root & health check endpoints.
- Location management and duplicate collision handling.
- Telemetry ingestion (Probe, Wi-Fi, Application).
- Automated incident generation and resolution.
- Campus experience dashboard summary calculations.
- Prescriptive recommendations retrieval.
- Crowdsourced user report logging.
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
from backend.models import Location, Incident

# Dedicated test SQLite database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
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
    """Initializes a clean database schema and seeds a base location before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    loc = Location(name="Test Location", latitude=1.29, longitude=103.77)
    db.add(loc)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


class TestSystemEndpoints:
    """Tests baseline root and health check endpoints."""

    def test_read_root(self):
        """Verifies root endpoint returns service metadata."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "CampusPulse API"
        assert data["message"] == "Welcome to CampusPulse API"

    def test_health_check(self):
        """Verifies health check endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestLocationEndpoints:
    """Tests location registration and query endpoints."""

    def test_create_location(self):
        """Verifies successful creation of a new campus location."""
        payload = {"name": "Library Annex", "latitude": 1.294, "longitude": 103.772}
        response = client.post("/api/locations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Library Annex"
        assert data["id"] is not None

    def test_create_duplicate_location_error(self):
        """Verifies error boundary triggers HTTP 400 on duplicate location name."""
        payload = {"name": "Test Location", "latitude": 1.29, "longitude": 103.77}
        response = client.post("/api/locations", json=payload)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_get_locations(self):
        """Verifies retrieving the list of all registered locations."""
        response = client.get("/api/locations")
        assert response.status_code == 200
        locations = response.json()
        assert len(locations) >= 1
        assert locations[0]["name"] == "Test Location"


class TestTelemetryIngestionEndpoints:
    """Tests probe, wifi, and application metric ingestion."""

    def test_create_probe_metric(self):
        """Verifies ingestion of valid probe metric."""
        payload = {"location_id": 1, "latency_ms": 22.5, "packet_loss_percent": 0.2}
        response = client.post("/api/probe", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["latency_ms"] == 22.5
        assert data["packet_loss_percent"] == 0.2

    def test_get_probe_metrics(self):
        """Verifies retrieval of historical probe metrics."""
        client.post("/api/probe", json={"location_id": 1, "latency_ms": 20.0, "packet_loss_percent": 0.0})
        response = client.get("/api/metrics/probe?limit=10&location_id=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_create_wifi_metric(self):
        """Verifies ingestion of Wi-Fi access point metrics."""
        payload = {"location_id": 1, "wifi_rssi": -65.0, "wifi_quality": 92.0, "connected_users": 28}
        response = client.post("/api/wifi", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["wifi_rssi"] == -65.0
        assert data["connected_users"] == 28

    def test_get_wifi_metrics(self):
        """Verifies retrieval of Wi-Fi metrics."""
        client.post("/api/wifi", json={"location_id": 1, "wifi_rssi": -62.0, "wifi_quality": 95.0, "connected_users": 15})
        response = client.get("/api/metrics/wifi?limit=5")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_create_application_metric(self):
        """Verifies ingestion of application synthetic transaction metrics."""
        payload = {"location_id": 1, "app_response_time_ms": 95.0, "app_status_code": 200}
        response = client.post("/api/application", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["app_response_time_ms"] == 95.0
        assert data["app_status_code"] == 200

    def test_get_application_metrics(self):
        """Verifies retrieval of application metrics."""
        client.post("/api/application", json={"location_id": 1, "app_response_time_ms": 110.0, "app_status_code": 200})
        response = client.get("/api/metrics/application?limit=5")
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestIncidentLifecycle:
    """Tests automated detection, creation, and auto-resolution of incidents."""

    def test_incident_creation_on_high_latency(self):
        """Verifies that submitting high latency metric triggers an active incident."""
        response = client.post("/api/probe", json={"location_id": 1, "latency_ms": 300.0, "packet_loss_percent": 0.0})
        assert response.status_code == 200

        incidents_resp = client.get("/api/incidents?status_filter=Active")
        assert incidents_resp.status_code == 200
        incidents = incidents_resp.json()
        assert len(incidents) > 0
        assert incidents[0]["severity"] == "Degraded"
        assert incidents[0]["status"] == "Active"

    def test_incident_auto_resolution(self):
        """Verifies that an active incident auto-resolves when metrics return to normal."""
        # 1. Trigger incident
        client.post("/api/probe", json={"location_id": 1, "latency_ms": 400.0, "packet_loss_percent": 15.0})
        active = client.get("/api/incidents?status_filter=Active").json()
        assert len(active) == 1

        # 2. Ingest normal telemetry to restore baseline
        client.post("/api/probe", json={"location_id": 1, "latency_ms": 20.0, "packet_loss_percent": 0.0})
        client.post("/api/wifi", json={"location_id": 1, "wifi_rssi": -60.0, "wifi_quality": 95.0, "connected_users": 20})
        client.post("/api/application", json={"location_id": 1, "app_response_time_ms": 80.0, "app_status_code": 200})

        # Incident should now be resolved
        resolved = client.get("/api/incidents?status_filter=Resolved").json()
        assert len(resolved) >= 1
        assert resolved[0]["duration_seconds"] is not None


class TestDashboardAndReports:
    """Tests dashboard aggregations and user feedback reports."""

    def test_dashboard_summary(self):
        """Verifies calculation of aggregated campus dashboard metrics."""
        client.post("/api/probe", json={"location_id": 1, "latency_ms": 25.0, "packet_loss_percent": 0.5})
        client.post("/api/wifi", json={"location_id": 1, "wifi_rssi": -60.0, "wifi_quality": 90.0, "connected_users": 15})
        client.post("/api/application", json={"location_id": 1, "app_response_time_ms": 100.0, "app_status_code": 200})

        response = client.get("/api/dashboard")
        assert response.status_code == 200
        summary = response.json()
        assert "score" in summary
        assert "avg_latency" in summary
        assert "avg_packet_loss" in summary
        assert "avg_wifi_quality" in summary
        assert "app_response_time" in summary
        assert summary["score"] > 80.0

    def test_user_report_creation_and_retrieval(self):
        """Verifies crowdsourced user report submission and listing."""
        report_payload = {
            "location_id": 1,
            "issue_type": "Wi-Fi Disconnections",
            "severity": "High",
            "description": "Laptops dropping off Wi-Fi repeatedly during lecture."
        }
        post_resp = client.post("/api/report", json=report_payload)
        assert post_resp.status_code == 200
        assert post_resp.json()["issue_type"] == "Wi-Fi Disconnections"

        get_resp = client.get("/api/reports")
        assert get_resp.status_code == 200
        reports = get_resp.json()
        assert len(reports) >= 1
        assert reports[0]["severity"] == "High"

    def test_recommendations_endpoint(self):
        """Verifies retrieval of recommendations for degraded incidents."""
        # Trigger an incident with recommendation
        client.post("/api/wifi", json={"location_id": 1, "wifi_rssi": -90.0, "wifi_quality": 30.0, "connected_users": 65})
        client.post("/api/probe", json={"location_id": 1, "latency_ms": 350.0, "packet_loss_percent": 0.0})

        response = client.get("/api/recommendations")
        assert response.status_code == 200
        recs = response.json()
        assert len(recs) >= 1
        assert "recommendation" in recs[0]
