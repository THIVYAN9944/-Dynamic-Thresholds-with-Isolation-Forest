"""
CampusPulse Database Configuration and Session Management.

This module initializes the SQLAlchemy ORM engine, declarative base model,
and database session generator with robust connection parameters and SQLite
concurrency optimizations for the CampusPulse monitoring system.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Ensure the data directory exists prior to creating the SQLite file
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Primary SQLite database URI
DB_PATH = os.path.join(DATA_DIR, "campuspulse.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create SQLAlchemy engine with multi-threading compatibility for FastAPI
# check_same_thread=False allows FastAPI worker threads to share connections safely
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

# Enforce foreign key constraints in SQLite (disabled by default in standard SQLite)
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enables SQLite Foreign Key constraints and Write-Ahead Logging (WAL) mode
    to boost concurrency and maintain relational referential integrity.
    """
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    except Exception:
        # Fallback gracefully if connection does not support pragmas (e.g. mock DBs)
        pass

# Factory for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for all SQLAlchemy ORM models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields an isolated database session per request.
    
    Guarantees session cleanup and connection return to the connection pool
    via a try-finally error boundary, preventing connection leaks.
    
    Yields:
        Session: Active SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
