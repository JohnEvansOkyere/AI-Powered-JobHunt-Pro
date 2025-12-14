"""
API Dependencies

Shared dependencies for authentication, authorization, and common operations.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import httpx

from app.core.database import get_db
from app.core.supabase_client import get_supabase_client, get_supabase_service_client
from app.core.config import settings
from supabase import Client

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependency to get current authenticated user from Supabase JWT.
    
    Verifies the JWT token and extracts user information.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        dict: User information from Supabase JWT
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    try:
        # Verify JWT token with Supabase
        # Use Supabase REST API to verify the token
        import httpx
        from app.core.config import settings
        
        # Call Supabase Auth API to verify token
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.SUPABASE_KEY,
                },
                timeout=5.0,
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
            
            user_data = response.json()
            
            return {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "email_confirmed_at": user_data.get("email_confirmed_at"),
                "user_metadata": user_data.get("user_metadata", {}),
                "created_at": user_data.get("created_at", ""),
            }
        
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        # Log the error for debugging
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"HTTP error verifying user token: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    except Exception as e:
        # Log the error for debugging
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error verifying user token: {e}")
        
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

