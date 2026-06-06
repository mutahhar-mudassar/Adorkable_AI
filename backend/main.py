"""
Adorkable AI - FastAPI Application Entry Point

Main FastAPI application with all routers and startup configuration.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.database import create_all_tables
from backend.config import UPLOAD_DIR, APP_ENV, CORS_ALLOWED_ORIGINS, SECRET_KEY

# Convert relative paths to absolute
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if UPLOAD_DIR.startswith('./'):
    UPLOAD_DIR = os.path.join(BASE_DIR, UPLOAD_DIR[2:])

# Import routers
from backend.auth import auth_router
from backend.routers import wardrobe, profile, recommendations, planner, combo, analytics


# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Lifecycle Management
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Runs on startup and shutdown.
    """
    # Startup
    logger.info("Starting up Adorkable AI...")

    # Security guard for non-development environments
    default_secret = "adorkable-secret-key-32-chars-long"
    if APP_ENV != "development" and SECRET_KEY == default_secret:
        raise RuntimeError("SECRET_KEY must be set in non-development environments.")
    
    # Create database tables
    await create_all_tables()
    logger.info("Database tables ready")
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory ready: {UPLOAD_DIR}")
    
    logger.info("Adorkable AI is ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Adorkable AI...")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Adorkable AI",
    description="Fashion Intelligence Platform - Your Personal AI Stylist",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# CORS Middleware
# =============================================================================

if CORS_ALLOWED_ORIGINS:
    allow_origins = CORS_ALLOWED_ORIGINS
    allow_credentials = True
else:
    # Dev-friendly defaults without wildcard+credentials conflict.
    allow_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Static Files
# =============================================================================

# Ensure upload directory exists before mounting
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount uploads directory for serving images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# =============================================================================
# API Routers
# =============================================================================

# Auth router (prefix already set in router)
app.include_router(auth_router, prefix="/api/v1")

# Wardrobe router
app.include_router(wardrobe.router, prefix="/api/v1")

# Profile router
app.include_router(profile.router, prefix="/api/v1")

# Recommendations router
app.include_router(recommendations.router, prefix="/api/v1")

# Planner router
app.include_router(planner.router, prefix="/api/v1")

# Combo router
app.include_router(combo.router, prefix="/api/v1")

# Analytics router
app.include_router(analytics.router, prefix="/api/v1")


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/")
async def root():
    """
    Root endpoint - health check.
    """
    return {
        "status": "Adorkable AI is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/v1")
async def api_root():
    """
    API root endpoint.
    """
    return {
        "message": "Welcome to Adorkable AI API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth",
            "wardrobe": "/api/v1/wardrobe",
            "profile": "/api/v1/profile",
            "recommend": "/api/v1/recommend",
            "plan": "/api/v1/plan",
            "combo": "/api/v1/combo",
            "analytics": "/api/v1/analytics"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "service": "adorkable-ai",
        "version": "1.0.0"
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler.
    """
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


# backend/main.py generated — Adorkable AI
