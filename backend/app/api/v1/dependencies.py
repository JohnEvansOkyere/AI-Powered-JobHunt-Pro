"""Shared API dependencies for authentication, authorization, and common operations."""

from typing import Optional
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import httpx

from app.core.logging import get_logger
from app.core.supabase_client import get_supabase_client
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from supabase import Client
from sqlalchemy.orm import Session

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
    jwt_secret = (getattr(settings, "auth_supabase_jwt_secret", "") or "").strip()
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
    db: Session = Depends(get_db),
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
        user_data = local_user
    else:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.auth_supabase_url}/auth/v1/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "apikey": settings.auth_supabase_key,
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

                auth_user = response.json()
                user_data = {
                    "id": auth_user.get("id"),
                    "email": auth_user.get("email"),
                    "email_confirmed_at": auth_user.get("email_confirmed_at"),
                    "user_metadata": auth_user.get("user_metadata", {}),
                    "created_at": auth_user.get("created_at", ""),
                }

        except HTTPException:
            raise
        except httpx.HTTPError as e:
            logger.error(
                "supabase_auth_http_error",
                error_type=type(e).__name__,
                message=str(e) or repr(e),
                supabase_url=settings.auth_supabase_url,
            )

            raise _unauthorized()
        except Exception as e:
            logger.error(
                "supabase_auth_unexpected_error",
                error_type=type(e).__name__,
                message=str(e) or repr(e),
            )

            raise _unauthorized()

    try:
        user_id = uuid.UUID(str(user_data.get("id")))
    except (ValueError, TypeError, AttributeError):
        raise _unauthorized("Invalid authentication credentials")

    account = db.query(User).filter(User.id == user_id).first()
    if not account:
        # A missing public.users row means the account was revoked or the
        # auth-to-profile trigger is not installed. Fail closed for protected APIs.
        raise _unauthorized("Account is not available")
    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Contact support if you believe this is a mistake.",
        )

    return user_data


security_optional = HTTPBearer(auto_error=False)
async def require_admin(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Allow only users whose public.users row has is_admin=true."""
    try:
        user_id = uuid.UUID(str(current_user.get("id")))
    except (ValueError, TypeError):
        user_id = None

    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db),
) -> Optional[dict]:
    """Like get_current_user but returns None for unauthenticated requests."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


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
