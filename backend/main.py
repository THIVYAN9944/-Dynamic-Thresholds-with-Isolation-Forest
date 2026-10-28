"""
CampusPulse Application Entrypoint.

Configures the FastAPI application instance, database schema creation,
global exception error boundaries, CORS middleware, and API router mounting.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from . import api

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("campuspulse.main")

# Auto-create database tables on startup if they do not exist
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application with comprehensive metadata
app = FastAPI(
    title="CampusPulse API",
    description=(
        "End-to-End Network Experience Recorder and Intermittent Degradation Localisation System. "
        "Provides real-time multi-tier telemetry ingestion, Isolation Forest dynamic anomaly detection, "
        "automated incident lifecycle resolution, and prescriptive recommendations."
    ),
    version="1.3.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure Cross-Origin Resource Sharing (CORS) for local Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Error Boundary: Catch unhandled exceptions and return structured JSON
@app.exception_handler(Exception)
async def global_exception_boundary_handler(request: Request, exc: Exception):
    """
    Top-level error boundary capturing any unexpected exceptions.
    Prevents raw stack trace leakage and guarantees uniform error responses.
    """
    logger.exception("Unhandled application exception at %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. The incident has been logged for investigation.",
            "path": request.url.path
        }
    )


# Mount core API endpoints
app.include_router(api.router, prefix="/api", tags=["CampusPulse Telemetry & Incidents"])


@app.get("/", tags=["Health"])
def read_root():
    """Root health check endpoint."""
    return {
        "status": "healthy",
        "service": "CampusPulse API",
        "version": "1.3.0",
        "message": "Welcome to CampusPulse API"
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe endpoint."""
    return {"status": "ok"}
