from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

class ProbeMetric(Base):
    __tablename__ = "probe_metrics"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    latency_ms = Column(Float)
    packet_loss_percent = Column(Float)
    
    location = relationship("Location")

class WifiMetric(Base):
    __tablename__ = "wifi_metrics"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    wifi_rssi = Column(Float)
    wifi_quality = Column(Float)
    connected_users = Column(Integer)
    
    location = relationship("Location")

class ApplicationMetric(Base):
    __tablename__ = "application_metrics"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    app_response_time_ms = Column(Float)
    app_status_code = Column(Integer)
    
    location = relationship("Location")

class UserReport(Base):
    __tablename__ = "user_reports"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    issue_type = Column(String)
    severity = Column(String)
    description = Column(String)
    
    location = relationship("Location")

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    incident_type = Column(String) # High Latency, Weak Wi-Fi, App Slowdown, Packet Loss, etc.
    severity = Column(String) # Warning, Degraded
    status = Column(String) # Active, Resolved
    metrics_before = Column(String, nullable=True) # JSON string
    metrics_during = Column(String, nullable=True) # JSON string
    metrics_after = Column(String, nullable=True) # JSON string
    cause_explanation = Column(String, nullable=True)
    recommendation = Column(String, nullable=True)
    
    location = relationship("Location")

class SystemEvent(Base):
    __tablename__ = "system_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    event_type = Column(String) # e.g., rollback_triggered, legacy_mode_enabled, prototype_mode_enabled, migration_completed
    description = Column(String)
