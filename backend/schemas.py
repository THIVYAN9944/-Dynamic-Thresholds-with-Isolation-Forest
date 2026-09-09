from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class LocationBase(BaseModel):
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class LocationCreate(LocationBase):
    pass

class Location(LocationBase):
    id: int
    class Config:
        from_attributes = True

class ProbeMetricCreate(BaseModel):
    location_id: int
    latency_ms: float
    packet_loss_percent: float
    timestamp: Optional[datetime] = None

class WifiMetricCreate(BaseModel):
    location_id: int
    wifi_rssi: float
    wifi_quality: float
    connected_users: int
    timestamp: Optional[datetime] = None

class ApplicationMetricCreate(BaseModel):
    location_id: int
    app_response_time_ms: float
    app_status_code: int
    timestamp: Optional[datetime] = None

class UserReportCreate(BaseModel):
    location_id: int
    issue_type: str
    severity: str
    description: str
    timestamp: Optional[datetime] = None

class IncidentCreate(BaseModel):
    location_id: int
    incident_type: str
    severity: str
    status: str
    metrics_before: Optional[str] = None
    metrics_during: Optional[str] = None
    metrics_after: Optional[str] = None
    cause_explanation: Optional[str] = None
    recommendation: Optional[str] = None
    start_time: datetime

class IncidentUpdate(BaseModel):
    status: str
    end_time: datetime
    duration_seconds: float
    metrics_after: Optional[str] = None

class SystemEventCreate(BaseModel):
    event_type: str
    description: str
