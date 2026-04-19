"""Shared API dependencies for authentication, authorization, and common operations."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import httpx

from app.core.logging import get_logger
from app.core.supabase_client import get_supabase_client
from app.core.config import settings
from supabase import Client

security = HTTPBearer()
logger = get_logger(__name__)


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _looks_like_jwt(token: str) -> bool:
    """Return true for compact JWT shape before attempting remote validation."""
    return bool(token and token.count(".") == 2)


def _verify_supabase_jwt_locally(token: str) -> dict | None:
    """
    Verify a Supabase access token without a network call when SUPABASE_JWT_SECRET is set.

    Supabase access tokens are JWTs whose subject is the user ID. Local validation avoids
    turning a temporary Supabase Auth network problem into a dashboard-wide 401 loop.
    """
    jwt_secret = (getattr(settings, "SUPABASE_JWT_SECRET", "") or "").strip()
    if not jwt_secret:
        return None

    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        logger.warning(
            "local_supabase_jwt_validation_failed",
            error_type=type(exc).__name__,
        )
        raise _unauthorized("Invalid authentication credentials")

    user_id = payload.get("sub")
    if not user_id:
        logger.warning("local_supabase_jwt_missing_subject")
        raise _unauthorized("Invalid authentication credentials")

    return {
        "id": user_id,
        "email": payload.get("email"),
        "email_confirmed_at": payload.get("email_confirmed_at") or payload.get("confirmed_at"),
        "user_metadata": payload.get("user_metadata", {}),
        "created_at": payload.get("created_at", ""),
    }


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

    if not _looks_like_jwt(token):
        raise _unauthorized("Invalid authentication credentials")

    local_user = _verify_supabase_jwt_locally(token)
    if local_user:
        return local_user
    
    try:
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
                logger.warning(
                    "supabase_token_rejected",
                    status_code=response.status_code,
                )
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
        logger.error(
            "supabase_auth_http_error",
            error_type=type(e).__name__,
            message=str(e) or repr(e),
            supabase_url=settings.SUPABASE_URL,
        )

        raise _unauthorized()
    except Exception as e:
        logger.error(
            "supabase_auth_unexpected_error",
            error_type=type(e).__name__,
            message=str(e) or repr(e),
        )

        raise _unauthorized()


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
