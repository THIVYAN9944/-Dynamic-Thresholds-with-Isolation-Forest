from fastapi import FastAPI
from .database import engine, Base
from . import api

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CampusPulse API", description="End-to-End Network Experience Recorder")

app.include_router(api.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to CampusPulse API"}
