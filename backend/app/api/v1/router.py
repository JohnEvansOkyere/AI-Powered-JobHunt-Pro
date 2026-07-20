"""
API v1 Router

Main router that includes all v1 API endpoints.
"""

from fastapi import APIRouter

# Import route modules
from app.api.v1.endpoints import (
    auth,
    profiles,
    users,
    cvs,
    ai,
    jobs,
    applications,
    recommendations,
    whatsapp,
    ops,
    analytics,
    admin,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(cvs.router, prefix="/cvs", tags=["cvs"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(ops.router, prefix="/ops", tags=["ops"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(
    whatsapp.router_notifications, prefix="/notifications", tags=["notifications"]
)
api_router.include_router(whatsapp.router_webhooks, prefix="/webhooks", tags=["webhooks"])
