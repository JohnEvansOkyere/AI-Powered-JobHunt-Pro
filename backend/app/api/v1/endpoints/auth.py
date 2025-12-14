"""
Authentication Endpoints

Handles user authentication using Supabase Auth.
Since Supabase handles most auth logic, these endpoints primarily
provide session validation and user info retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.api.v1.dependencies import get_current_user, get_supabase
from app.core.logging import get_logger
from supabase import Client

logger = get_logger(__name__)

router = APIRouter()


class UserResponse(BaseModel):
    """User information response model."""
    id: str
    email: Optional[str] = None
    email_verified: bool = False
    user_metadata: dict = {}
    created_at: str


class SessionResponse(BaseModel):
    """Session validation response."""
    valid: bool
    user: Optional[UserResponse] = None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
):
    """
    Get current authenticated user information.
    
    Returns:
        UserResponse: Current user information
    """
    try:
        return UserResponse(
            id=current_user.get("id"),
            email=current_user.get("email"),
            email_verified=current_user.get("email_confirmed_at") is not None,
            user_metadata=current_user.get("user_metadata", {}),
            created_at=current_user.get("created_at", ""),
        )
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information",
        )


@router.get("/session", response_model=SessionResponse)
async def validate_session(
    current_user: dict = Depends(get_current_user),
):
    """
    Validate current session.
    
    Returns:
        SessionResponse: Session validation result
    """
    try:
        return SessionResponse(
            valid=True,
            user=UserResponse(
                id=current_user.get("id"),
                email=current_user.get("email"),
                email_verified=current_user.get("email_confirmed_at") is not None,
                user_metadata=current_user.get("user_metadata", {}),
                created_at=current_user.get("created_at", ""),
            ),
        )
    except HTTPException:
        return SessionResponse(valid=False, user=None)
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        return SessionResponse(valid=False, user=None)


@router.post("/logout")
async def logout(
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """
    Logout current user.
    
    Note: Supabase handles logout on the client side.
    This endpoint is for server-side session cleanup if needed.
    
    Returns:
        dict: Logout confirmation
    """
    try:
        # Supabase logout is typically handled client-side
        # This endpoint can be used for server-side cleanup
        logger.info(f"User {current_user.get('id')} logged out")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout",
        )

