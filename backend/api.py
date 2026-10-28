"""
CampusPulse FastAPI Route Handlers and Endpoints.

Provides RESTful endpoints for telemetry ingestion, historical telemetry retrieval,
real-time incident lifecycle management, crowdsourced user feedback, and campus dashboard analytics.
Includes robust input validation, transactional error boundaries, and ML fallback mechanisms.
"""

import os
import sys
import json
import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from . import models, schemas
from .database import get_db

# Ensure services directory is accessible on the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import detection, recommendation

logger = logging.getLogger("campuspulse.api")

router = APIRouter()


def check_and_create_incident(db: Session, location_id: int) -> None:
    """
    Evaluates current and historical location metrics to manage automated incident lifecycle.

    Error Boundaries:
    - Tier-1: Queries the latest probe, wifi, and application metrics for the given location.
    - Tier-2: Feeds recent history (up to 100 samples) to the dynamic Isolation Forest model.
      If the ML detection engine raises an uncaught exception, falls back to the static heuristic engine.
    - Tier-3: State Machine Resolution:
        * If status == 'Degraded' and no active incident exists -> Creates a new Incident with remediation.
        * If status == 'Healthy' and an active incident exists -> Resolves the Incident with duration calculation.
    - Tier-4: Database rollback on commit failure to prevent transaction corruption.

    Args:
        db: SQLAlchemy active database session.
        location_id: Campus location identifier being evaluated.
    """
    try:
        # Fetch latest metrics for this location
        probe = db.query(models.ProbeMetric).filter(
            models.ProbeMetric.location_id == location_id
        ).order_by(models.ProbeMetric.timestamp.desc()).first()

        wifi = db.query(models.WifiMetric).filter(
            models.WifiMetric.location_id == location_id
        ).order_by(models.WifiMetric.timestamp.desc()).first()

        app = db.query(models.ApplicationMetric).filter(
            models.ApplicationMetric.location_id == location_id
        ).order_by(models.ApplicationMetric.timestamp.desc()).first()

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

        # Fetch recent historical baseline (up to 100 observations)
        past_probes = db.query(models.ProbeMetric).filter(
            models.ProbeMetric.location_id == location_id
        ).order_by(models.ProbeMetric.timestamp.desc()).limit(100).all()

        past_wifis = db.query(models.WifiMetric).filter(
            models.WifiMetric.location_id == location_id
        ).order_by(models.WifiMetric.timestamp.desc()).limit(100).all()

        past_apps = db.query(models.ApplicationMetric).filter(
            models.ApplicationMetric.location_id == location_id
        ).order_by(models.ApplicationMetric.timestamp.desc()).limit(100).all()

        historical_data = []
        for p, w, a in zip(past_probes, past_wifis, past_apps):
            historical_data.append({
                "latency_ms": p.latency_ms,
                "packet_loss_percent": p.packet_loss_percent,
                "wifi_rssi": w.wifi_rssi,
                "app_response_time_ms": a.app_response_time_ms
            })

        # Error Boundary: ML Evaluation with Graceful Static Heuristic Fallback
        try:
            status_flag, anomalies = detection.detect_anomaly_ml(
                current_metrics=current_ml_metrics,
                historical_data=historical_data,
                location_id=location_id
            )
        except Exception as ml_err:
            logger.warning(
                "ML dynamic detection failed for location %s: %s. Falling back to static thresholds.",
                location_id, ml_err
            )
            status_flag, anomalies = detection.detect_anomaly(
                latency=latency,
                packet_loss=packet_loss,
                wifi_rssi=wifi_rssi,
                app_response=app_response
            )

        # Check for active incident for this location
        active_incident = db.query(models.Incident).filter(
            models.Incident.location_id == location_id,
            models.Incident.status == "Active"
        ).first()

        current_metrics_snapshot = {
            "latency_ms": latency,
            "packet_loss_percent": packet_loss,
            "wifi_rssi": wifi_rssi,
            "app_response_time_ms": app_response,
            "connected_users": wifi.connected_users if wifi else 0
        }

        now_utc = datetime.now(timezone.utc)

        if status_flag == "Degraded" and not active_incident:
            # Generate prescriptive remediation
            rec = recommendation.generate_recommendation(anomalies, current_metrics_snapshot)
            new_inc = models.Incident(
                location_id=location_id,
                incident_type=", ".join(anomalies),
                severity="Degraded",
                status="Active",
                start_time=now_utc,
                metrics_during=json.dumps(current_metrics_snapshot),
                cause_explanation=f"System detected degradation: {', '.join(anomalies)}",
                recommendation=rec
            )
            db.add(new_inc)
            db.commit()
            logger.info("New incident opened for location %s: %s", location_id, anomalies)

        elif status_flag == "Healthy" and active_incident:
            # Auto-resolve incident as metrics returned to nominal baseline
            active_incident.status = "Resolved"
            active_incident.end_time = now_utc
            # Calculate total duration in seconds safely
            start_t = active_incident.start_time
            if start_t.tzinfo is None:
                start_t = start_t.replace(tzinfo=timezone.utc)
            active_incident.duration_seconds = max(0.0, (now_utc - start_t).total_seconds())
            active_incident.metrics_after = json.dumps(current_metrics_snapshot)
            db.commit()
            logger.info("Active incident %s auto-resolved for location %s", active_incident.id, location_id)

    except SQLAlchemyError as db_err:
        db.rollback()
        logger.error("Database error during incident evaluation for location %s: %s", location_id, db_err)
    except Exception as general_err:
        logger.error("Unexpected error during incident evaluation: %s", general_err)


# ============================================================================
# Telemetry Ingestion Endpoints (Probe, Wi-Fi, Application)
# ============================================================================

@router.post("/probe", response_model=schemas.ProbeMetricCreate, status_code=status.HTTP_200_OK)
def create_probe_metric(metric: schemas.ProbeMetricCreate, db: Session = Depends(get_db)):
    """
    Ingests synthetic or ICMP probe telemetry metrics (latency and packet loss).

    Error Boundary:
    - Verifies that target location_id exists (raises 404 if missing).
    - Rolls back database transaction on commit error (raises 500).
    - Triggers automated incident lifecycle checks asynchronously.
    """
    location = db.query(models.Location).filter(models.Location.id == metric.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {metric.location_id} does not exist."
        )

    try:
        db_metric = models.ProbeMetric(**metric.model_dump())
        db.add(db_metric)
        db.commit()
        db.refresh(db_metric)
    except SQLAlchemyError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist probe metric: {str(err)}"
        )

    check_and_create_incident(db, metric.location_id)
    return db_metric


@router.get("/metrics/probe")
def get_probe_metrics(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to retrieve"),
    location_id: Optional[int] = Query(None, description="Filter metrics by location ID")
):
    """
    Retrieves historical probe telemetry records ordered by timestamp descending.
    """
    query = db.query(models.ProbeMetric)
    if location_id is not None:
        query = query.filter(models.ProbeMetric.location_id == location_id)
    return query.order_by(models.ProbeMetric.timestamp.desc()).limit(limit).all()


@router.post("/wifi", response_model=schemas.WifiMetricCreate, status_code=status.HTTP_200_OK)
def create_wifi_metric(metric: schemas.WifiMetricCreate, db: Session = Depends(get_db)):
    """
    Ingests wireless access point telemetry (RSSI, link quality, client count).

    Error Boundary:
    - Verifies location_id existence (raises 404 if not found).
    - Rolls back transaction on database exception.
    - Evaluates location for wireless degradation incidents.
    """
    location = db.query(models.Location).filter(models.Location.id == metric.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {metric.location_id} does not exist."
        )

    try:
        db_metric = models.WifiMetric(**metric.model_dump())
        db.add(db_metric)
        db.commit()
        db.refresh(db_metric)
    except SQLAlchemyError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist Wi-Fi metric: {str(err)}"
        )

    check_and_create_incident(db, metric.location_id)
    return db_metric


@router.get("/metrics/wifi")
def get_wifi_metrics(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to retrieve"),
    location_id: Optional[int] = Query(None, description="Filter metrics by location ID")
):
    """
    Retrieves historical Wi-Fi telemetry records ordered by timestamp descending.
    """
    query = db.query(models.WifiMetric)
    if location_id is not None:
        query = query.filter(models.WifiMetric.location_id == location_id)
    return query.order_by(models.WifiMetric.timestamp.desc()).limit(limit).all()


@router.post("/application", response_model=schemas.ApplicationMetricCreate, status_code=status.HTTP_200_OK)
def create_app_metric(metric: schemas.ApplicationMetricCreate, db: Session = Depends(get_db)):
    """
    Ingests synthetic HTTP application response time and status code metrics.

    Error Boundary:
    - Enforces location existence (raises 404 if missing).
    - Transactional commit with rollback on database failure.
    - Triggers incident lifecycle checks.
    """
    location = db.query(models.Location).filter(models.Location.id == metric.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {metric.location_id} does not exist."
        )

    try:
        db_metric = models.ApplicationMetric(**metric.model_dump())
        db.add(db_metric)
        db.commit()
        db.refresh(db_metric)
    except SQLAlchemyError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist application metric: {str(err)}"
        )

    check_and_create_incident(db, metric.location_id)
    return db_metric


@router.get("/metrics/application")
def get_app_metrics(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to retrieve"),
    location_id: Optional[int] = Query(None, description="Filter metrics by location ID")
):
    """
    Retrieves historical application telemetry records ordered by timestamp descending.
    """
    query = db.query(models.ApplicationMetric)
    if location_id is not None:
        query = query.filter(models.ApplicationMetric.location_id == location_id)
    return query.order_by(models.ApplicationMetric.timestamp.desc()).limit(limit).all()


# ============================================================================
# User Crowdsourced Reporting Endpoints
# ============================================================================

@router.post("/report", response_model=schemas.UserReportCreate, status_code=status.HTTP_200_OK)
def create_user_report(report: schemas.UserReportCreate, db: Session = Depends(get_db)):
    """
    Submits crowdsourced student/faculty feedback regarding network slowness.

    Error Boundary:
    - Validates target location_id (raises 404 if not found).
    - Validates severity pattern ('Low', 'Medium', 'High') via Pydantic.
    """
    location = db.query(models.Location).filter(models.Location.id == report.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {report.location_id} does not exist."
        )

    try:
        db_report = models.UserReport(**report.model_dump())
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report
    except SQLAlchemyError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save user report: {str(err)}"
        )


@router.get("/reports")
def get_user_reports(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500, description="Maximum reports to retrieve")
):
    """
    Retrieves recent user reports ordered by timestamp descending.
    """
    return db.query(models.UserReport).order_by(models.UserReport.timestamp.desc()).limit(limit).all()


# ============================================================================
# Location Management Endpoints
# ============================================================================

@router.get("/locations", response_model=List[schemas.Location])
def get_locations(db: Session = Depends(get_db)):
    """
    Lists all configured campus locations and monitoring zones.
    """
    return db.query(models.Location).all()


@router.post("/locations", response_model=schemas.Location, status_code=status.HTTP_200_OK)
def create_location(location: schemas.LocationCreate, db: Session = Depends(get_db)):
    """
    Registers a new campus monitoring location.

    Error Boundary:
    - Checks for duplicate location name (raises 400 Bad Request if already exists).
    - Validates coordinates boundary via Pydantic schema (-90 to +90 lat, -180 to +180 lon).
    """
    existing = db.query(models.Location).filter(models.Location.name == location.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location with name '{location.name}' already exists."
        )

    try:
        db_loc = models.Location(**location.model_dump())
        db.add(db_loc)
        db.commit()
        db.refresh(db_loc)
        return db_loc
    except SQLAlchemyError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register location: {str(err)}"
        )


# ============================================================================
# Dashboard Summary & System Health Analytics
# ============================================================================

@router.get("/dashboard")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Calculates aggregated real-time campus network experience analytics.

    Returns:
    - score: Overall Campus Experience Score (0-100) using empirical formula.
    - avg_latency: Recent average probe latency (ms).
    - avg_packet_loss: Recent average packet drop rate (%).
    - avg_wifi_quality: Recent average Wi-Fi link score (0-100).
    - app_response_time: Recent average application TTFB (ms).
    - active_incidents: Count of currently open network degradations.
    - user_reports: Total user-submitted feedback entries.
    """
    probe_metrics = db.query(models.ProbeMetric).order_by(models.ProbeMetric.timestamp.desc()).limit(20).all()
    wifi_metrics = db.query(models.WifiMetric).order_by(models.WifiMetric.timestamp.desc()).limit(20).all()
    app_metrics = db.query(models.ApplicationMetric).order_by(models.ApplicationMetric.timestamp.desc()).limit(20).all()

    avg_latency = (sum(m.latency_ms for m in probe_metrics) / len(probe_metrics)) if probe_metrics else 20.0
    avg_packet_loss = (sum(m.packet_loss_percent for m in probe_metrics) / len(probe_metrics)) if probe_metrics else 0.0
    avg_wifi_quality = (sum(m.wifi_quality for m in wifi_metrics) / len(wifi_metrics)) if wifi_metrics else 100.0
    avg_app_time = (sum(m.app_response_time_ms for m in app_metrics) / len(app_metrics)) if app_metrics else 100.0

    active_incidents = db.query(models.Incident).filter(models.Incident.status == "Active").count()
    user_reports_count = db.query(models.UserReport).count()

    # Utilize modular experience score service
    health_score = detection.calculate_experience_score(
        latency=avg_latency,
        packet_loss=avg_packet_loss,
        wifi_quality=avg_wifi_quality,
        app_response=avg_app_time
    )

    return {
        "score": round(health_score, 1),
        "avg_latency": round(avg_latency, 2),
        "avg_packet_loss": round(avg_packet_loss, 2),
        "avg_wifi_quality": round(avg_wifi_quality, 2),
        "app_response_time": round(avg_app_time, 2),
        "active_incidents": active_incidents,
        "user_reports": user_reports_count
    }


# ============================================================================
# Incidents and Prescriptive Recommendations
# ============================================================================

@router.get("/incidents")
def get_incidents(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Maximum incident records to retrieve"),
    status_filter: Optional[str] = Query(None, description="Filter by status: 'Active' or 'Resolved'")
):
    """
    Retrieves detected network degradation incidents.
    """
    query = db.query(models.Incident)
    if status_filter:
        query = query.filter(models.Incident.status == status_filter)
    return query.order_by(models.Incident.start_time.desc()).limit(limit).all()


@router.post("/incidents", response_model=schemas.IncidentCreate, status_code=status.HTTP_200_OK)
def create_incident(incident: schemas.IncidentCreate, db: Session = Depends(get_db)):
    """
    Manually creates or imports an incident record into the ledger.

    Error Boundary:
    - Validates location existence (raises 404 if missing).
    - Database commit error handling with rollback.
    """
    location = db.query(models.Location).filter(models.Location.id == incident.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {incident.location_id} does not exist."
        )

    try:
        db_inc = models.Incident(**incident.model_dump())
        db.add(db_inc)
        db.commit()
        db.refresh(db_inc)
        return db_inc
    except SQLAlchemyError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record incident: {str(err)}"
        )


@router.get("/recommendations")
def get_recommendations(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50, description="Maximum recommendations to return")
):
    """
    Returns actionable remediation guidance for recent network incidents.
    """
    incidents = db.query(models.Incident).filter(
        models.Incident.recommendation != None
    ).order_by(models.Incident.start_time.desc()).limit(limit).all()

    return [
        {
            "id": i.id,
            "incident": i.incident_type,
            "location_id": i.location_id,
            "status": i.status,
            "recommendation": i.recommendation,
            "start_time": i.start_time.isoformat() if i.start_time else None
        }
        for i in incidents
    ]
