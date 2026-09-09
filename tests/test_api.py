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

# Setup test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
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
    loc = Location(name="Test Location")
    db.add(loc)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to CampusPulse API"}

def test_create_location():
    response = client.post("/api/locations", json={"name": "New Loc", "latitude": 1.0, "longitude": 1.0})
    assert response.status_code == 200
    assert response.json()["name"] == "New Loc"

def test_create_probe_metric():
    response = client.post("/api/probe", json={"location_id": 1, "latency_ms": 20, "packet_loss_percent": 0.0})
    assert response.status_code == 200
    assert response.json()["latency_ms"] == 20.0

def test_incident_creation_on_high_latency():
    response = client.post("/api/probe", json={"location_id": 1, "latency_ms": 300, "packet_loss_percent": 0.0})
    assert response.status_code == 200
    
    incidents = client.get("/api/incidents").json()
    assert len(incidents) > 0
    assert incidents[0]["severity"] == "Degraded"
