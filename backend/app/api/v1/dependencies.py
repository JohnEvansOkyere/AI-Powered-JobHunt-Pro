"""
API Dependencies

Shared dependencies for authentication, authorization, and common operations.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.supabase_client import get_supabase_client
from supabase import Client

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """
    Dependency to get current authenticated user from Supabase JWT.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        dict: User information from Supabase
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    supabase: Client = get_supabase_client()
    
    try:
        # Verify token with Supabase
        user = supabase.auth.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return user.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def get_supabase(
    supabase: Client = Depends(get_supabase_client),
) -> Client:
    """
    Dependency to get Supabase client.
    
    Args:
        supabase: Supabase client instance
        
    Returns:
        Client: Supabase client
    """
    return supabase

