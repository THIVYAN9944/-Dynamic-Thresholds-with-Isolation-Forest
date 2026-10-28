"""
CampusPulse Database Models.

Defines the SQLAlchemy ORM models representing the complete telemetry schema,
location inventory, incident records, user reports, and system audit logs.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


def get_utc_now() -> datetime:
    """Helper to return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Location(Base):
    """
    Physical campus location or network monitoring zone.
    
    Serves as the central parent entity for all spatial telemetry streams,
    incidents, and user tickets.
    """
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,
                  doc="Unique auto-incrementing location identifier.")
    name = Column(String(128), unique=True, index=True, nullable=False,
                  doc="Human-readable campus zone name (e.g. 'Classroom Block A').")
    latitude = Column(Float, nullable=True,
                      doc="Geographic latitude coordinate for campus GIS mapping.")
    longitude = Column(Float, nullable=True,
                       doc="Geographic longitude coordinate for campus GIS mapping.")

    # Relationships to telemetry streams and incidents
    probe_metrics = relationship("ProbeMetric", back_populates="location", cascade="all, delete-orphan")
    wifi_metrics = relationship("WifiMetric", back_populates="location", cascade="all, delete-orphan")
    application_metrics = relationship("ApplicationMetric", back_populates="location", cascade="all, delete-orphan")
    user_reports = relationship("UserReport", back_populates="location", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="location", cascade="all, delete-orphan")


class ProbeMetric(Base):
    """
    Network-layer probe metrics (ICMP / Synthetic synthetic probes).
    
    Measures latency and packet drop rates between local vantage points
    and campus default gateways / upstream infrastructure.
    """
    __tablename__ = "probe_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,
                  doc="Primary key for the probe metric record.")
    timestamp = Column(DateTime, default=get_utc_now, index=True, nullable=False,
                       doc="UTC timestamp when the probe measurement was sampled.")
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True,
                         doc="Foreign key referencing the associated campus location.")
    latency_ms = Column(Float, nullable=False,
                        doc="Round-trip time in milliseconds (RTT).")
    packet_loss_percent = Column(Float, nullable=False,
                                doc="Percentage of dropped probe packets (0.0% - 100.0%).")

    # Many-to-one relationship with Location
    location = relationship("Location", back_populates="probe_metrics")


class WifiMetric(Base):
    """
    Wireless access point telemetry metrics.
    
    Captures physical layer and link-quality signal metrics from Wi-Fi APs
    and connected station telemetry.
    """
    __tablename__ = "wifi_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,
                  doc="Primary key for the Wi-Fi metric record.")
    timestamp = Column(DateTime, default=get_utc_now, index=True, nullable=False,
                       doc="UTC timestamp when the Wi-Fi metric was recorded.")
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True,
                         doc="Foreign key referencing the associated campus location.")
    wifi_rssi = Column(Float, nullable=False,
                      doc="Received Signal Strength Indication in dBm (e.g. -75 dBm to -50 dBm).")
    wifi_quality = Column(Float, nullable=False,
                          doc="Link quality score (0.0 to 100.0).")
    connected_users = Column(Integer, nullable=False, default=0,
                             doc="Total active clients connected to the local AP.")

    # Many-to-one relationship with Location
    location = relationship("Location", back_populates="wifi_metrics")


class ApplicationMetric(Base):
    """
    Application-layer telemetry metrics.
    
    Tracks synthetic HTTP transaction health, TTFB (time-to-first-byte),
    and HTTP status codes for critical campus services (e.g. LMS, ERP).
    """
    __tablename__ = "application_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,
                  doc="Primary key for the application metric record.")
    timestamp = Column(DateTime, default=get_utc_now, index=True, nullable=False,
                       doc="UTC timestamp of the synthetic HTTP request.")
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True,
                         doc="Foreign key referencing the associated campus location.")
    app_response_time_ms = Column(Float, nullable=False,
                                  doc="HTTP round-trip response time in milliseconds.")
    app_status_code = Column(Integer, nullable=False, default=200,
                             doc="HTTP response status code returned by the upstream service.")

    # Many-to-one relationship with Location
    location = relationship("Location", back_populates="application_metrics")


class UserReport(Base):
    """
    Manual crowdsourced incident feedback from campus students and faculty.
    
    Correlated against automated machine telemetry to validate intermittent
    degradations and bridge subjective perceptions with empirical metrics.
    """
    __tablename__ = "user_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,
                  doc="Primary key for the user report.")
    timestamp = Column(DateTime, default=get_utc_now, index=True, nullable=False,
                       doc="UTC timestamp when the report was submitted.")
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True,
                         doc="Foreign key referencing the affected campus location.")
    issue_type = Column(String(64), nullable=False,
                        doc="Category of reported issue (e.g., 'Slow Browsing', 'Disconnects').")
    severity = Column(String(32), nullable=False,
                      doc="User-assessed urgency level: 'Low', 'Medium', or 'High'.")
    description = Column(Text, nullable=True,
                         doc="Freeform textual description provided by the user.")

    # Many-to-one relationship with Location
    location = relationship("Location", back_populates="user_reports")


class Incident(Base):
    """
    Network degradation or anomaly incident record.
    
    Generated automatically by the ML/heuristic anomaly detection engine
    when performance parameters deviate from historical baselines.
    """
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,
                  doc="Primary key for the incident log entry.")
    start_time = Column(DateTime, default=get_utc_now, index=True, nullable=False,
                        doc="UTC timestamp when the degradation began.")
    end_time = Column(DateTime, nullable=True,
                      doc="UTC timestamp when the metrics returned to a healthy baseline.")
    duration_seconds = Column(Float, nullable=True,
                              doc="Total duration of the degradation in seconds.")
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True,
                         doc="Foreign key referencing the degraded campus location.")
    incident_type = Column(String(128), nullable=False,
                          doc="Classification of anomaly (e.g. 'High Latency, Weak Wi-Fi').")
    severity = Column(String(32), nullable=False, default="Degraded",
                      doc="System severity rating: 'Warning', 'Degraded', or 'Critical'.")
    status = Column(String(32), nullable=False, default="Active", index=True,
                    doc="Incident resolution status: 'Active' or 'Resolved'.")
    metrics_before = Column(Text, nullable=True,
                            doc="JSON snapshot of metric baseline prior to degradation.")
    metrics_during = Column(Text, nullable=True,
                            doc="JSON snapshot of degraded metrics sampled at incident inception.")
    metrics_after = Column(Text, nullable=True,
                           doc="JSON snapshot of recovery metrics captured upon incident resolution.")
    cause_explanation = Column(Text, nullable=True,
                               doc="Heuristic explanation of detected anomalies.")
    recommendation = Column(Text, nullable=True,
                            doc="Prescriptive action generated by the recommendation service.")

    # Many-to-one relationship with Location
    location = relationship("Location", back_populates="incidents")


class SystemEvent(Base):
    """
    Audit log of administrative and architecture lifecycle events.
    
    Records state changes such as prototype/legacy mode toggles, rollbacks,
    and legacy CSV data migrations.
    """
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,
                  doc="Primary key for the system audit event.")
    timestamp = Column(DateTime, default=get_utc_now, nullable=False, index=True,
                       doc="UTC timestamp of the system event.")
    event_type = Column(String(64), nullable=False, index=True,
                        doc="Identifier: 'rollback_triggered', 'migration_completed', etc.")
    description = Column(Text, nullable=False,
                         doc="Human-readable contextual explanation of the event.")
