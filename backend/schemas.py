"""
CampusPulse Data Validation and Serialization Schemas.

Utilizes Pydantic v2 to enforce strict input validation, data boundaries,
and serialization schemas across all REST API endpoints.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class LocationBase(BaseModel):
    """Base schema for location attributes."""
    name: str = Field(..., min_length=1, max_length=128, description="Unique human-readable location name.")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to +90).")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to +180).")


class LocationCreate(LocationBase):
    """Schema for creating a new location entity."""
    pass


class Location(LocationBase):
    """Schema for serialized location entity including database primary key."""
    id: int = Field(..., description="Unique database identifier.")
    model_config = ConfigDict(from_attributes=True)


class ProbeMetricCreate(BaseModel):
    """
    Schema for ingesting network layer probe metrics.
    Enforces non-negative latency and valid packet loss bounds (0-100%).
    """
    location_id: int = Field(..., ge=1, description="Database ID of the corresponding location.")
    latency_ms: float = Field(..., ge=0.0, description="ICMP/Synthetic probe latency in milliseconds (>= 0).")
    packet_loss_percent: float = Field(..., ge=0.0, le=100.0, description="Packet loss percentage (0.0 to 100.0%).")
    timestamp: Optional[datetime] = Field(None, description="Sampling UTC timestamp (auto-generated if omitted).")

    model_config = ConfigDict(from_attributes=True)


class WifiMetricCreate(BaseModel):
    """
    Schema for ingesting Wi-Fi telemetry metrics.
    Enforces valid RSSI range (-120 to 0 dBm), quality (0-100), and non-negative users.
    """
    location_id: int = Field(..., ge=1, description="Database ID of the corresponding location.")
    wifi_rssi: float = Field(..., ge=-120.0, le=0.0, description="Signal strength in dBm (-120.0 to 0.0).")
    wifi_quality: float = Field(..., ge=0.0, le=100.0, description="Wi-Fi link quality score (0.0 to 100.0).")
    connected_users: int = Field(..., ge=0, description="Concurrent connected station count (>= 0).")
    timestamp: Optional[datetime] = Field(None, description="Sampling UTC timestamp (auto-generated if omitted).")

    model_config = ConfigDict(from_attributes=True)


class ApplicationMetricCreate(BaseModel):
    """
    Schema for ingesting application synthetic transaction telemetry.
    Enforces non-negative response time and valid HTTP status code bounds (100-599).
    """
    location_id: int = Field(..., ge=1, description="Database ID of the corresponding location.")
    app_response_time_ms: float = Field(..., ge=0.0, description="HTTP time-to-first-byte in milliseconds (>= 0).")
    app_status_code: int = Field(..., ge=100, le=599, description="Standard HTTP status code (100 to 599).")
    timestamp: Optional[datetime] = Field(None, description="Sampling UTC timestamp (auto-generated if omitted).")

    model_config = ConfigDict(from_attributes=True)


class UserReportCreate(BaseModel):
    """
    Schema for crowdsourced user degradation reports.
    """
    location_id: int = Field(..., ge=1, description="Target location ID experiencing issues.")
    issue_type: str = Field(..., min_length=1, max_length=64, description="Category of the reported failure.")
    severity: str = Field(..., pattern="^(Low|Medium|High)$", description="Severity grade: 'Low', 'Medium', or 'High'.")
    description: Optional[str] = Field("", max_length=1000, description="Freeform context of the failure.")
    timestamp: Optional[datetime] = Field(None, description="Report UTC timestamp.")

    model_config = ConfigDict(from_attributes=True)


class IncidentCreate(BaseModel):
    """
    Schema for creating or logging an incident record.
    """
    location_id: int = Field(..., ge=1, description="Location ID where the degradation occurred.")
    incident_type: str = Field(..., min_length=1, max_length=128, description="Anomaly classification.")
    severity: str = Field(..., pattern="^(Warning|Degraded|Critical)$", description="Severity category.")
    status: str = Field(..., pattern="^(Active|Resolved)$", description="Current status.")
    metrics_before: Optional[str] = Field(None, description="JSON string of prior baseline metrics.")
    metrics_during: Optional[str] = Field(None, description="JSON string of metrics during the degradation.")
    metrics_after: Optional[str] = Field(None, description="JSON string of recovery metrics.")
    cause_explanation: Optional[str] = Field(None, description="Root-cause diagnostic summary.")
    recommendation: Optional[str] = Field(None, description="Prescriptive remediation guidance.")
    start_time: datetime = Field(..., description="Timestamp when the incident started.")

    model_config = ConfigDict(from_attributes=True)


class IncidentUpdate(BaseModel):
    """
    Schema for updating and resolving an active incident.
    """
    status: str = Field("Resolved", pattern="^(Active|Resolved)$", description="Updated incident status.")
    end_time: datetime = Field(..., description="Timestamp when degradation resolved.")
    duration_seconds: float = Field(..., ge=0.0, description="Duration in seconds.")
    metrics_after: Optional[str] = Field(None, description="JSON string of recovery telemetry.")

    model_config = ConfigDict(from_attributes=True)


class SystemEventCreate(BaseModel):
    """
    Schema for logging audit trail events.
    """
    event_type: str = Field(..., min_length=1, max_length=64, description="Event classification key.")
    description: str = Field(..., min_length=1, description="Detailed event summary.")

    model_config = ConfigDict(from_attributes=True)
