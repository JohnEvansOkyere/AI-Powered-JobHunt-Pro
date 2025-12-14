"""
API v1 Router

Main router that includes all v1 API endpoints.
"""

from fastapi import APIRouter

# Import route modules (will be created in subsequent phases)
# from app.api.v1.endpoints import auth, profiles, jobs, applications

api_router = APIRouter()

# Include endpoint routers
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
# api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
# api_router.include_router(applications.router, prefix="/applications", tags=["applications"])

