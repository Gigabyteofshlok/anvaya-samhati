from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db, engine, Base
import app.models  # ensure models registered
from app.api.router import api_router

app = FastAPI(
    title="ANVAYA SAṂHATI",
    description="Enterprise AI-Native Hospital Operating System (Phases 1–4 Combined)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include master API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/api/health", tags=["System"])
def api_health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy (PostgreSQL)"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online",
        "system": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": db_status
    }

@app.get("/", tags=["System"])
def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "tagline": "Connecting every part of a hospital into one intelligent system.",
        "documentation": "/docs"
    }
