"""API v1 router assembly.

Route order matters: the literal ``/fixtures/today`` must be registered before the
``/fixtures/{match_id}`` parameter route.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import fixtures, health, reference, sync

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(fixtures.router)
api_router.include_router(reference.router)
api_router.include_router(sync.router)

__all__ = ["api_router"]
