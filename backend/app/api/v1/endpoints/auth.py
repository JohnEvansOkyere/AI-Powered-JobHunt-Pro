"""
Authentication Endpoints

Handles user authentication using Supabase Auth.
Since Supabase handles most auth logic, these endpoints primarily
provide session validation and user info retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.api.v1.dependencies import get_current_user, get_supabase
from app.core.config import settings
from app.core.logging import get_logger
from supabase import Client

logger = get_logger(__name__)

router = APIRouter()

HANDOFF_TOKEN_ISSUER = "veloxarecruit"
HANDOFF_TOKEN_AUDIENCE = "veloxahire"
HANDOFF_TOKEN_PURPOSE = "ats_apply"


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


class HandoffVerifyRequest(BaseModel):
    token: str


class HandoffVerifyResponse(BaseModel):
    valid: bool
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    job_id: Optional[str] = None


def _decode_handoff_token(token: str) -> dict:
    if not settings.HANDOFF_TOKEN_SECRET:
        raise JWTError("HANDOFF_TOKEN_SECRET is not configured")

    decode_kwargs = {
        "algorithms": ["HS256"],
        "audience": HANDOFF_TOKEN_AUDIENCE,
        "issuer": HANDOFF_TOKEN_ISSUER,
    }
    try:
        payload = jwt.decode(token, settings.HANDOFF_TOKEN_SECRET, **decode_kwargs)
    except JWTError:
        if not settings.PREVIOUS_HANDOFF_TOKEN_SECRET:
            raise
        payload = jwt.decode(token, settings.PREVIOUS_HANDOFF_TOKEN_SECRET, **decode_kwargs)

    if payload.get("purpose") != HANDOFF_TOKEN_PURPOSE:
        raise JWTError("Invalid handoff token purpose")
    if not payload.get("email"):
        raise JWTError("Handoff token missing email")
    return payload


@router.post("/handoff/verify", response_model=HandoffVerifyResponse)
async def verify_handoff_token(payload: HandoffVerifyRequest):
    """Verify an ATS signup handoff token and return safe prefill fields."""
    try:
        claims = _decode_handoff_token(payload.token)
        return HandoffVerifyResponse(
            valid=True,
            email=claims.get("email"),
            full_name=claims.get("full_name"),
            phone=claims.get("phone"),
            job_id=claims.get("job_id"),
        )
    except Exception as exc:
        logger.info("handoff_token_invalid", error=str(exc))
        return HandoffVerifyResponse(valid=False)


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
