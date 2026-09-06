"""One-time phone verification must be established by Supabase, never metadata."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1 import dependencies


@pytest.fixture
def auth_setup(monkeypatch):
    user = {
        "id": "11111111-1111-4111-8111-111111111111",
        "email": "candidate@example.test",
        "phone": "233241234567",
        "phone_confirmed_at": "2026-09-06T00:00:00Z",
        "user_metadata": {},
    }
    monkeypatch.setattr(dependencies, "_verify_supabase_jwt_locally", lambda token: None)
    transport = AsyncMock()
    transport.get.return_value = httpx.Response(200, json=user)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=transport)
    context.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(dependencies.httpx, "AsyncClient", lambda: context)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(is_active=True)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test.access.token")
    return user, transport, db, credentials


@pytest.mark.asyncio
async def test_verified_password_session_requires_no_new_otp(auth_setup):
    user, transport, db, credentials = auth_setup
    for _ in range(2):
        result = await dependencies.get_current_user(credentials, db)
        assert result["id"] == user["id"]
    assert transport.get.await_count == 2
    assert all(call.args[0].endswith('/auth/v1/user') for call in transport.get.call_args_list)
    transport.post.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("phone,confirmed", [(None, None), ("233241234567", None), ("", "2026-09-06")])
async def test_unverified_accounts_cannot_use_protected_api(auth_setup, phone, confirmed):
    user, transport, db, credentials = auth_setup
    user.update(phone=phone, phone_confirmed_at=confirmed)
    user["user_metadata"] = {"phone_verified": True, "phone_confirmed_at": "2026-09-06"}
    transport.get.return_value = httpx.Response(200, json=user)
    with pytest.raises(HTTPException) as error:
        await dependencies.get_current_user(credentials, db)
    assert error.value.status_code == 403
    assert error.value.detail == "Phone verification required"
    assert await dependencies.get_optional_user(credentials, db) is None


@pytest.mark.asyncio
async def test_standard_local_jwt_fetches_authoritative_phone_status(auth_setup, monkeypatch):
    user, transport, db, credentials = auth_setup
    local_user = {**user, "phone_confirmed_at": None, "user_metadata": {"phone_verified": True}}
    monkeypatch.setattr(dependencies, "_verify_supabase_jwt_locally", lambda token: local_user)
    result = await dependencies.get_current_user(credentials, db)
    assert result["phone_confirmed_at"] == user["phone_confirmed_at"]
    transport.get.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("account,status", [(None, 401), (SimpleNamespace(is_active=False), 403)])
async def test_phone_verification_does_not_bypass_revocation(auth_setup, account, status):
    _, _, db, credentials = auth_setup
    db.query.return_value.filter.return_value.first.return_value = account
    with pytest.raises(HTTPException) as error:
        await dependencies.get_current_user(credentials, db)
    assert error.value.status_code == status


@pytest.mark.asyncio
async def test_auth_lookup_failure_fails_closed(auth_setup):
    _, transport, db, credentials = auth_setup
    transport.get.side_effect = httpx.ConnectError('Synthetic provider outage')
    with pytest.raises(HTTPException) as error:
        await dependencies.get_current_user(credentials, db)
    assert error.value.status_code == 401
