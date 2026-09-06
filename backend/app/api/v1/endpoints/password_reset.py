"""Public SMS recovery endpoints; authorization is the one-use reset grant."""

import hmac
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services import password_reset as recovery

router = APIRouter(prefix='/password-reset')


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    phone: str = Field(min_length=8, max_length=32)

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, value):
        return recovery.normalize_phone(value)


class ResetVerify(BaseModel):
    model_config = ConfigDict(extra='forbid')
    challenge_id: str = Field(pattern=r'^[A-Za-z0-9_-]{43}$')
    code: str = Field(pattern=r'^[0-9]{6}$')


class ResetComplete(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reset_token: SecretStr = Field(min_length=43, max_length=43)
    password: SecretStr = Field(min_length=12, max_length=128)


def client_ip(request: Request):
    # Trust only ASGI's peer. Configure Uvicorn's trusted proxy addresses at
    # deployment; never accept a caller-supplied X-Forwarded-For here.
    return request.client.host if request.client else 'unknown'


def no_store(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'


@router.post('/request', status_code=202)
async def request_reset(payload: ResetRequest, request: Request, response: Response,
                        background: BackgroundTasks, db: Session = Depends(get_db)):
    no_store(response)
    challenge = await recovery.create_challenge(payload.phone, client_ip(request))
    # Local row is only a lookup hint, never proof of phone/email ownership.
    account = db.query(User).filter(User.phone_e164.in_([payload.phone, payload.phone.lstrip('+')]), User.is_active.is_(True)).first()
    background.add_task(recovery.deliver_challenge, challenge, str(account.id) if account else None, payload.phone)
    return dict(message=recovery.GENERIC_MESSAGE, challenge_id=challenge, expires_in=recovery.CODE_TTL, resend_after=60)


@router.post('/verify')
async def verify_reset(payload: ResetVerify, request: Request, response: Response):
    no_store(response)
    grant = await recovery.verify_challenge(payload.challenge_id, payload.code, client_ip(request))
    return dict(reset_token=grant, expires_in=recovery.GRANT_TTL)


@router.post('/complete')
async def complete_reset(payload: ResetComplete, request: Request, response: Response, db: Session = Depends(get_db)):
    no_store(response)
    grant = await recovery.consume_grant(payload.reset_token.get_secret_value(), client_ip(request))
    account = db.query(User).filter(User.id == uuid.UUID(grant['user_id']), User.is_active.is_(True)).first()
    if not account:
        raise HTTPException(400, recovery.INVALID_GRANT)
    current = await recovery.auth_user(grant['user_id'])
    if not current or not recovery.verified_identity(current, grant['user_id']) or not hmac.compare_digest(grant['binding'], recovery.identity_binding(current)):
        raise HTTPException(400, recovery.INVALID_GRANT)
    await recovery.change_password(grant['user_id'], payload.password.get_secret_value())
    return dict(message='Your password has been reset. Sign in with your email and new password.')
