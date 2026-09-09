from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json

from . import models, schemas
from .database import get_db
import sys
import os

# Add parent to path for services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import detection, recommendation

router = APIRouter()

def check_and_create_incident(db: Session, location_id: int):
    # Get latest metrics
    probe = db.query(models.ProbeMetric).filter(models.ProbeMetric.location_id == location_id).order_by(models.ProbeMetric.timestamp.desc()).first()
    wifi = db.query(models.WifiMetric).filter(models.WifiMetric.location_id == location_id).order_by(models.WifiMetric.timestamp.desc()).first()
    app = db.query(models.ApplicationMetric).filter(models.ApplicationMetric.location_id == location_id).order_by(models.ApplicationMetric.timestamp.desc()).first()
    
    latency = probe.latency_ms if probe else None
    packet_loss = probe.packet_loss_percent if probe else None
    wifi_rssi = wifi.wifi_rssi if wifi else None
    app_response = app.app_response_time_ms if app else None
    
    current_ml_metrics = {
        "latency_ms": latency,
        "packet_loss_percent": packet_loss,
        "wifi_rssi": wifi_rssi,
        "app_response_time_ms": app_response
    }
    
    # Fetch historical data for ML dynamic thresholds
    past_probes = db.query(models.ProbeMetric).filter(models.ProbeMetric.location_id == location_id).order_by(models.ProbeMetric.timestamp.desc()).limit(100).all()
    past_wifis = db.query(models.WifiMetric).filter(models.WifiMetric.location_id == location_id).order_by(models.WifiMetric.timestamp.desc()).limit(100).all()
    past_apps = db.query(models.ApplicationMetric).filter(models.ApplicationMetric.location_id == location_id).order_by(models.ApplicationMetric.timestamp.desc()).limit(100).all()
    
    historical_data = []
    for p, w, a in zip(past_probes, past_wifis, past_apps):
        historical_data.append({
            "latency_ms": p.latency_ms,
            "packet_loss_percent": p.packet_loss_percent,
            "wifi_rssi": w.wifi_rssi,
            "app_response_time_ms": a.app_response_time_ms
        })
        
    status, anomalies = detection.detect_anomaly_ml(current_ml_metrics, historical_data)
    
    # Check if there is an active incident for this location
    active_incident = db.query(models.Incident).filter(
        models.Incident.location_id == location_id,
        models.Incident.status == "Active"
    ).first()
    
    current_metrics = {
        "latency_ms": latency,
        "packet_loss_percent": packet_loss,
        "wifi_rssi": wifi_rssi,
        "app_response_time_ms": app_response,
        "connected_users": wifi.connected_users if wifi else 0
    }
    
    if status == "Degraded" and not active_incident:
        # Create new incident
        rec = recommendation.generate_recommendation(anomalies, current_metrics)
        new_inc = models.Incident(
            location_id=location_id,
            incident_type=", ".join(anomalies),
            severity="Degraded",
            status="Active",
            start_time=datetime.utcnow(),
            metrics_during=json.dumps(current_metrics),
            cause_explanation=f"System detected: {', '.join(anomalies)}",
            recommendation=rec
        )
        db.add(new_inc)
        db.commit()
    elif status == "Healthy" and active_incident:
        # Resolve incident
        active_incident.status = "Resolved"
        active_incident.end_time = datetime.utcnow()
        active_incident.duration_seconds = (active_incident.end_time - active_incident.start_time).total_seconds()
        active_incident.metrics_after = json.dumps(current_metrics)
        db.commit()

@router.post("/probe", response_model=schemas.ProbeMetricCreate)
def create_probe_metric(metric: schemas.ProbeMetricCreate, db: Session = Depends(get_db)):
    db_metric = models.ProbeMetric(**metric.model_dump())
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    check_and_create_incident(db, metric.location_id)
    return db_metric

@router.get("/metrics/probe")
def get_probe_metrics(db: Session = Depends(get_db), limit: int = 100):
    metrics = db.query(models.ProbeMetric).order_by(models.ProbeMetric.timestamp.desc()).limit(limit).all()
    return metrics

@router.post("/wifi", response_model=schemas.WifiMetricCreate)
def create_wifi_metric(metric: schemas.WifiMetricCreate, db: Session = Depends(get_db)):
    db_metric = models.WifiMetric(**metric.model_dump())
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    check_and_create_incident(db, metric.location_id)
    return db_metric

@router.get("/metrics/wifi")
def get_wifi_metrics(db: Session = Depends(get_db), limit: int = 100):
    metrics = db.query(models.WifiMetric).order_by(models.WifiMetric.timestamp.desc()).limit(limit).all()
    return metrics

@router.post("/application", response_model=schemas.ApplicationMetricCreate)
def create_app_metric(metric: schemas.ApplicationMetricCreate, db: Session = Depends(get_db)):
    db_metric = models.ApplicationMetric(**metric.model_dump())
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    check_and_create_incident(db, metric.location_id)
    return db_metric

@router.get("/metrics/application")
def get_app_metrics(db: Session = Depends(get_db), limit: int = 100):
    metrics = db.query(models.ApplicationMetric).order_by(models.ApplicationMetric.timestamp.desc()).limit(limit).all()
    return metrics

@router.post("/report", response_model=schemas.UserReportCreate)
def create_user_report(report: schemas.UserReportCreate, db: Session = Depends(get_db)):
    db_report = models.UserReport(**report.model_dump())
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@router.get("/locations", response_model=List[schemas.Location])
def get_locations(db: Session = Depends(get_db)):
    return db.query(models.Location).all()

@router.post("/locations", response_model=schemas.Location)
def create_location(location: schemas.LocationCreate, db: Session = Depends(get_db)):
    db_loc = models.Location(**location.model_dump())
    db.add(db_loc)
    db.commit()
    db.refresh(db_loc)
    return db_loc

@router.get("/dashboard")
def get_dashboard_summary(db: Session = Depends(get_db)):
    # Basic summary to be extended
    probe_metrics = db.query(models.ProbeMetric).order_by(models.ProbeMetric.timestamp.desc()).limit(10).all()
    wifi_metrics = db.query(models.WifiMetric).order_by(models.WifiMetric.timestamp.desc()).limit(10).all()
    app_metrics = db.query(models.ApplicationMetric).order_by(models.ApplicationMetric.timestamp.desc()).limit(10).all()
    
    avg_latency = sum([m.latency_ms for m in probe_metrics]) / len(probe_metrics) if probe_metrics else 0
    avg_packet_loss = sum([m.packet_loss_percent for m in probe_metrics]) / len(probe_metrics) if probe_metrics else 0
    avg_wifi_quality = sum([m.wifi_quality for m in wifi_metrics]) / len(wifi_metrics) if wifi_metrics else 0
    avg_app_time = sum([m.app_response_time_ms for m in app_metrics]) / len(app_metrics) if app_metrics else 0
    
    active_incidents = db.query(models.Incident).filter(models.Incident.status == 'Active').count()
    user_reports = db.query(models.UserReport).count()
    
    # Calculate score placeholder
    health_score = 100 - (avg_latency / 10) - (avg_packet_loss * 2) - ((100 - avg_wifi_quality) / 2)
    health_score = max(0, min(100, health_score))
    
    return {
        "score": round(health_score, 1),
        "avg_latency": round(avg_latency, 2),
        "avg_packet_loss": round(avg_packet_loss, 2),
        "avg_wifi_quality": round(avg_wifi_quality, 2),
        "app_response_time": round(avg_app_time, 2),
        "active_incidents": active_incidents,
        "user_reports": user_reports
    }

@router.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    return db.query(models.Incident).order_by(models.Incident.start_time.desc()).limit(50).all()

@router.post("/incidents", response_model=schemas.IncidentCreate)
def create_incident(incident: schemas.IncidentCreate, db: Session = Depends(get_db)):
    db_inc = models.Incident(**incident.model_dump())
    db.add(db_inc)
    db.commit()
    db.refresh(db_inc)
    return db_inc

@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    # Returns latest incidents with recommendations
    incidents = db.query(models.Incident).filter(models.Incident.recommendation != None).order_by(models.Incident.start_time.desc()).limit(10).all()
    return [{"incident": i.incident_type, "location_id": i.location_id, "recommendation": i.recommendation} for i in incidents]
