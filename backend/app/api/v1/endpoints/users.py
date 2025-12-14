"""
User Endpoints

Handles user information synced from Supabase Auth.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    email_verified: bool = False
    last_login_at: Optional[str] = None
    user_metadata: Optional[Dict[str, Any]] = {}
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update model."""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    user_metadata: Optional[Dict[str, Any]] = None


@router.get("/me", response_model=UserResponse)
async def get_my_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user information from public.users table.
    
    Returns:
        UserResponse: User information
    """
    try:
        user_id_str = current_user.get("id")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID",
            )
        user_id = uuid.UUID(str(user_id_str))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user ID format: {user_id_str}, error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # User might not be synced yet, return from auth data
        return UserResponse(
            id=current_user.get("id", ""),
            email=current_user.get("email"),
            full_name=current_user.get("user_metadata", {}).get("full_name"),
            email_verified=current_user.get("email_confirmed_at") is not None,
            user_metadata=current_user.get("user_metadata", {}),
            created_at=current_user.get("created_at", ""),
            updated_at=current_user.get("updated_at", ""),
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        user_metadata=user.user_metadata or {},
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
    )


@router.put("/me", response_model=UserResponse)
async def update_my_user_info(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user information.
    
    Args:
        user_data: User data to update
        
    Returns:
        UserResponse: Updated user information
    """
    try:
        user_id_str = current_user.get("id")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID",
            )
        user_id = uuid.UUID(str(user_id_str))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user ID format: {user_id_str}, error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # Create user record if it doesn't exist
        user = User(
            id=user_id,
            email=current_user.get("email"),
            email_verified=current_user.get("email_confirmed_at") is not None,
            user_metadata=current_user.get("user_metadata", {}),
        )
        db.add(user)
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "user_metadata" and user.user_metadata:
            # Merge metadata instead of replacing
            user.user_metadata = {**(user.user_metadata or {}), **(value or {})}
        else:
            # Map user_metadata to the actual column name
            if key == "user_metadata":
                setattr(user, "user_metadata", value)
            else:
                setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Updated user {user_id}")
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        user_metadata=user.user_metadata or {},
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
    )

