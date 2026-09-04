"""Versioned API router — mount domain routers here as they are added."""

from fastapi import APIRouter

from backend.api import health

v1_router = APIRouter()
v1_router.include_router(health.router)
