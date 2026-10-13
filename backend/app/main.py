"""Sky Force FastAPI Application Entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    aircraft,
    airports,
    conflicts,
    congestion,
    experiments,
    health,
    models,
    quality,
    routing,
    scenarios,
    weather,
)
from app.api.state import init_app_state
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing Sky Force application state...")
    try:
        init_app_state()
        logger.info("Sky Force application state initialized successfully.")
    except Exception as exc:
        logger.error("Error during startup state initialization: %s", exc)
    yield
    logger.info("Shutting down Sky Force application.")


settings = get_settings()

app = FastAPI(
    title="Sky Force: Predictive Airspace Analysis & Route Optimization API",
    description=(
        "Research prototype for spatial airspace analysis, ML congestion & travel-time prediction, "
        "graph-based multi-objective route planning, dynamic rerouting, and conflict analysis.\n\n"
        "DISCLAIMER: Research prototype for simulation and decision support. "
        "Not approved for operational flight planning, navigation, or air traffic control."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Custom Error Handlers
register_error_handlers(app)

# Include API Routers under /api
api_prefix = "/api"
app.include_router(health.router, prefix=api_prefix)
app.include_router(airports.router, prefix=api_prefix)
app.include_router(aircraft.router, prefix=api_prefix)
app.include_router(weather.router, prefix=api_prefix)
app.include_router(quality.router, prefix=api_prefix)
app.include_router(congestion.router, prefix=api_prefix)
app.include_router(routing.router, prefix=api_prefix)
app.include_router(scenarios.router, prefix=api_prefix)
app.include_router(conflicts.router, prefix=api_prefix)
app.include_router(experiments.router, prefix=api_prefix)
app.include_router(models.router, prefix=api_prefix)


@app.get("/")
def root():
    return {
        "project": "Sky Force",
        "description": "AI-Driven Framework for Predictive Airspace Analysis, Explainable Route Optimisation, and Dynamic Rerouting",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/api/health",
        "disclaimer": "Research prototype for simulation and decision support. Not approved for operational flight planning, navigation, or air traffic control.",
    }
