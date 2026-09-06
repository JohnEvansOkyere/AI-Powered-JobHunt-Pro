"""SMS recovery regressions. Redis tests require PASSWORD_RESET_TEST_REDIS_URL.

Use an isolated Redis (never production). Only unique test-prefix keys are removed.
Auth administration and SMS delivery are mocked; Redis Lua runs unchanged.
"""

import asyncio
import json
import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis

from app.api.v1.endpoints import password_reset as endpoints
from app.core.database import get_db
from app.services import password_reset as recovery

EMAIL = 'candidate@example.com'
PHONE = '+233241234567'
IP = '192.0.2.1'
USER_ID = '11111111-1111-4111-8111-111111111111'
PASSWORD = 'Synthetic-reset-password-123'


@pytest_asyncio.fixture
async def state(monkeypatch):
    url = os.getenv('PASSWORD_RESET_TEST_REDIS_URL')
    if not url:
        pytest.skip('Set PASSWORD_RESET_TEST_REDIS_URL to isolated Redis for atomic recovery tests')
    redis = Redis.from_url(url, decode_responses=True)
    await redis.ping()
    prefix = f'test:{{password-reset}}:{uuid.uuid4()}:'
    monkeypatch.setattr(recovery, 'PREFIX', prefix)
    monkeypatch.setattr(recovery, 'get_async_redis', AsyncMock(return_value=redis))
    monkeypatch.setattr(recovery.settings, 'AUTH_SUPABASE_SERVICE_KEY', 'synthetic-service-key')
    user = dict(id=USER_ID, email=EMAIL, phone=PHONE.lstrip('+'), phone_confirmed_at='2026-09-06T00:00:00Z', updated_at='2026-09-06T00:00:00Z')
    lookup = AsyncMock(return_value=user)
    sender = SimpleNamespace(send_auth_code=AsyncMock())
    monkeypatch.setattr(recovery, 'sms_providers', lambda: [('test', sender)])
    monkeypatch.setattr(recovery, 'auth_user', lookup)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=uuid.UUID(USER_ID), is_active=True)
    app = FastAPI()
    app.include_router(endpoints.router, prefix='/api/v1/auth')
    app.dependency_overrides[get_db] = lambda: db
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        yield SimpleNamespace(redis=redis, user=user, lookup=lookup, sender=sender, db=db, client=client)
    keys = [key async for key in redis.scan_iter(match=prefix + '*')]
    if keys:
        await redis.delete(*keys)
    await redis.aclose()


async def issued(state):
    challenge = await recovery.create_challenge(PHONE, IP)
    await recovery.deliver_challenge(challenge, USER_ID, PHONE)
    code = state.sender.send_auth_code.call_args.kwargs['otp']
    return challenge, code


async def expire_cooldown(state):
    # Expire only the synthetic cooldown, without sleeping or changing production logic.
    key = recovery.PREFIX + 'limit:request-cooldown:' + recovery.digest('limit', PHONE)
    await state.redis.delete(key)


@pytest.mark.asyncio
async def test_complete_flow_updates_only_verified_account_password(state, monkeypatch):
    change = AsyncMock()
    monkeypatch.setattr(recovery, 'change_password', change)
    response = await state.client.post('/api/v1/auth/password-reset/request', json={'phone': '024 123 4567'})
    assert response.status_code == 202
    assert response.headers['cache-control'] == 'no-store'
    challenge = response.json()['challenge_id']
    code = state.sender.send_auth_code.call_args.kwargs['otp']
    assert state.sender.send_auth_code.call_args.kwargs['purpose'] == 'password_reset'
    assert state.sender.send_auth_code.call_args.kwargs['phone_e164'] == PHONE
    verified = await state.client.post('/api/v1/auth/password-reset/verify', json={'challenge_id': challenge, 'code': code})
    assert verified.status_code == 200
    token = verified.json()['reset_token']
    assert 'access_token' not in verified.json()
    response = await state.client.post('/api/v1/auth/password-reset/complete', json={'reset_token': token, 'password': PASSWORD})
    assert response.status_code == 200
    change.assert_awaited_once_with(USER_ID, PASSWORD)
    replay = await state.client.post('/api/v1/auth/password-reset/complete', json={'reset_token': token, 'password': PASSWORD})
    assert replay.status_code == 400
    assert change.await_count == 1


@pytest.mark.asyncio
async def test_hashed_codes_and_grants_never_store_secrets_or_contacts(state):
    challenge, code = await issued(state)
    raw = await state.redis.get(recovery.PREFIX + 'code:' + challenge)
    assert json.loads(raw)['code_hash'] != code
    assert EMAIL not in raw and PHONE not in raw
    grant = await recovery.verify_challenge(challenge, code, IP)
    keys = [key async for key in state.redis.scan_iter(match=recovery.PREFIX + '*')]
    assert not any(grant in key or EMAIL in key or PHONE in key for key in keys)
    grant_data = await state.redis.get(recovery.PREFIX + 'grant:' + recovery.digest('grant', grant))
    assert grant not in grant_data and 'password' not in json.loads(grant_data)


@pytest.mark.asyncio
@pytest.mark.parametrize('change', [{'phone_confirmed_at': None}, {'phone': '233200000000'}, {'email': ''}, {'id': str(uuid.uuid4())}, {'banned_until': '2099-01-01T00:00:00Z'}])
async def test_authoritative_mismatch_never_sends_sms(state, change):
    state.user.update(change)
    challenge = await recovery.create_challenge(PHONE, IP)
    await recovery.deliver_challenge(challenge, USER_ID, PHONE)
    state.sender.send_auth_code.assert_not_awaited()
    with pytest.raises(HTTPException):
        await recovery.verify_challenge(challenge, '000000', IP)


@pytest.mark.asyncio
async def test_unknown_account_same_response_and_no_sms(state):
    state.db.query.return_value.filter.return_value.first.return_value = None
    result = await state.client.post('/api/v1/auth/password-reset/request', json={'phone': PHONE})
    assert result.status_code == 202
    assert result.json()['message'] == recovery.GENERIC_MESSAGE
    assert set(result.json()) == {'message', 'challenge_id', 'expires_in', 'resend_after'}
    state.sender.send_auth_code.assert_not_awaited()


@pytest.mark.asyncio
async def test_code_lockout_after_five_wrong_attempts(state):
    challenge, code = await issued(state)
    wrong = '111111' if code != '111111' else '222222'
    for _ in range(5):
        with pytest.raises(HTTPException):
            await recovery.verify_challenge(challenge, wrong, IP)
    with pytest.raises(HTTPException):
        await recovery.verify_challenge(challenge, code, IP)
    assert not await state.redis.exists(recovery.PREFIX + 'code:' + challenge)


@pytest.mark.asyncio
async def test_attempts_before_delivery_are_not_reset(state):
    challenge = await recovery.create_challenge(PHONE, IP)
    for _ in range(4):
        with pytest.raises(HTTPException):
            await recovery.verify_challenge(challenge, '000000', IP)
    await recovery.deliver_challenge(challenge, USER_ID, PHONE)
    raw = json.loads(await state.redis.get(recovery.PREFIX + 'code:' + challenge))
    assert raw['attempts'] == 4


@pytest.mark.asyncio
async def test_code_expiry_and_unknown_challenge_fail(state):
    challenge, code = await issued(state)
    key = recovery.PREFIX + 'code:' + challenge
    assert 0 < await state.redis.ttl(key) <= 300
    await state.redis.pexpire(key, 1)
    await asyncio.sleep(.01)
    for target in [challenge, 'x' * 43]:
        with pytest.raises(HTTPException):
            await recovery.verify_challenge(target, code, IP)


@pytest.mark.asyncio
async def test_concurrent_code_and_grant_consumption_have_one_winner(state):
    challenge, code = await issued(state)
    verified = await asyncio.gather(*(recovery.verify_challenge(challenge, code, IP) for _ in range(8)), return_exceptions=True)
    winners = [result for result in verified if isinstance(result, str)]
    assert len(winners) == 1
    consumed = await asyncio.gather(*(recovery.consume_grant(winners[0], IP) for _ in range(8)), return_exceptions=True)
    assert len([result for result in consumed if isinstance(result, dict)]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('verify_first', [False, True])
async def test_resend_invalidates_old_code_and_grant(state, verify_first):
    challenge, code = await issued(state)
    grant = await recovery.verify_challenge(challenge, code, IP) if verify_first else None
    await expire_cooldown(state)
    await recovery.create_challenge(PHONE, IP)
    with pytest.raises(HTTPException):
        if grant:
            await recovery.consume_grant(grant, IP)
        else:
            await recovery.verify_challenge(challenge, code, IP)


@pytest.mark.asyncio
async def test_grant_expires(state):
    challenge, code = await issued(state)
    grant = await recovery.verify_challenge(challenge, code, IP)
    key = recovery.PREFIX + 'grant:' + recovery.digest('grant', grant)
    assert 0 < await state.redis.ttl(key) <= 300
    await state.redis.pexpire(key, 1)
    await asyncio.sleep(.01)
    with pytest.raises(HTTPException):
        await recovery.consume_grant(grant, IP)


@pytest.mark.asyncio
@pytest.mark.parametrize('change', [{'phone': '233200000000'}, {'email': 'other@example.com'}, {'updated_at': '2026-09-07T00:00:00Z'}, {'phone_confirmed_at': None}])
async def test_identity_change_after_verification_blocks_reset(state, monkeypatch, change):
    challenge, code = await issued(state)
    grant = await recovery.verify_challenge(challenge, code, IP)
    state.user.update(change)
    update = AsyncMock()
    monkeypatch.setattr(recovery, 'change_password', update)
    result = await state.client.post('/api/v1/auth/password-reset/complete', json={'reset_token': grant, 'password': PASSWORD})
    assert result.status_code == 400
    update.assert_not_awaited()


@pytest.mark.asyncio
async def test_suspended_or_revoked_account_cannot_reset(state, monkeypatch):
    challenge, code = await issued(state)
    grant = await recovery.verify_challenge(challenge, code, IP)
    state.db.query.return_value.filter.return_value.first.return_value = None
    update = AsyncMock()
    monkeypatch.setattr(recovery, 'change_password', update)
    result = await state.client.post('/api/v1/auth/password-reset/complete', json={'reset_token': grant, 'password': PASSWORD})
    assert result.status_code == 400
    update.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_failover_and_failed_delivery_invalidates_code(state, monkeypatch):
    first = SimpleNamespace(send_auth_code=AsyncMock(side_effect=RuntimeError('synthetic outage')))
    monkeypatch.setattr(recovery, 'sms_providers', lambda: [('first', first), ('second', state.sender)])
    challenge, code = await issued(state)
    first.send_auth_code.assert_awaited_once()
    state.sender.send_auth_code.assert_awaited_once()
    await recovery.verify_challenge(challenge, code, IP)
    await expire_cooldown(state)
    state.sender.send_auth_code.side_effect = RuntimeError('synthetic outage')
    next_challenge = await recovery.create_challenge(PHONE, IP)
    await recovery.deliver_challenge(next_challenge, USER_ID, PHONE)
    assert not await state.redis.exists(recovery.PREFIX + 'code:' + next_challenge)


@pytest.mark.asyncio
async def test_mandatory_rate_limit_ignores_global_disable(state, monkeypatch):
    monkeypatch.setattr(recovery.settings, 'RATE_LIMIT_ENABLED', False)
    await recovery.create_challenge(PHONE, IP)
    with pytest.raises(HTTPException) as error:
        await recovery.create_challenge(PHONE, IP)
    assert error.value.status_code == 429
    assert int(error.value.headers['Retry-After']) > 0


@pytest.mark.asyncio
async def test_redis_outage_never_sends_or_verifies(monkeypatch):
    monkeypatch.setattr(recovery, 'get_async_redis', AsyncMock(side_effect=RuntimeError('offline')))
    for operation in [recovery.verify_challenge('a' * 43, '123456', IP), recovery.consume_grant('b' * 43, IP)]:
        with pytest.raises(HTTPException) as error:
            await operation
        assert error.value.status_code == 503


def test_separate_auth_project_never_uses_data_service_key(monkeypatch):
    monkeypatch.setattr(recovery.settings, 'AUTH_SUPABASE_SERVICE_KEY', '')
    monkeypatch.setattr(recovery.settings, 'AUTH_SUPABASE_URL', 'https://other.example.test')
    assert recovery.settings.auth_supabase_service_key == ''
    with pytest.raises(HTTPException):
        recovery.require_configuration()


@pytest.mark.parametrize('value', ['024 123 4567', '233241234567', '+233241234567'])
def test_ghana_phone_normalization(value):
    assert recovery.normalize_phone(value) == PHONE


def test_client_ip_does_not_trust_forged_forwarded_header():
    from starlette.requests import Request
    request = Request({'type': 'http', 'headers': [(b'x-forwarded-for', b'203.0.113.7')], 'client': (IP, 1234)})
    assert endpoints.client_ip(request) == IP


def test_validation_does_not_log_or_echo_passwords_or_codes(client, monkeypatch):
    from app.middleware import error_handler
    log = MagicMock()
    monkeypatch.setattr(error_handler, 'logger', log)
    response = client.post('/api/v1/auth/password-reset/complete', json={'reset_token': 'private-grant-value', 'password': 'private-secret'})
    assert response.status_code == 422
    assert 'private-grant-value' not in response.text
    assert 'private-secret' not in response.text
    assert log.warning.called
    assert 'private-secret' not in str(log.mock_calls)
    assert 'private-grant-value' not in str(log.mock_calls)
    assert response.headers['cache-control'] == 'no-store'


def test_oversized_reset_payload_rejected(client):
    response = client.post('/api/v1/auth/password-reset/request', json={'phone': '0' * 5000})
    assert response.status_code == 413
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [200, 422, 503])
async def test_admin_password_update_contract_and_failures(monkeypatch, status):
    monkeypatch.setattr(recovery.settings, 'AUTH_SUPABASE_URL', 'https://canonical.example.test')
    monkeypatch.setattr(recovery.settings, 'AUTH_SUPABASE_SERVICE_KEY', 'synthetic-auth-service')
    transport = AsyncMock()
    transport.put.return_value = httpx.Response(status, json={'id': USER_ID}, request=httpx.Request('PUT', 'https://canonical.example.test'))
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=transport)
    context.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(recovery.httpx, 'AsyncClient', lambda **kwargs: context)
    if status == 200:
        await recovery.change_password(USER_ID, PASSWORD)
    else:
        with pytest.raises(HTTPException):
            await recovery.change_password(USER_ID, PASSWORD)
    kwargs = transport.put.call_args.kwargs
    assert kwargs['json'] == {'password': PASSWORD}
    assert kwargs['headers']['apikey'] == 'synthetic-auth-service'
    assert transport.put.call_args.args[0] == f'https://canonical.example.test/auth/v1/admin/users/{USER_ID}'


@pytest.mark.asyncio
async def test_ambiguous_password_update_cannot_reuse_grant(state, monkeypatch):
    challenge, code = await issued(state)
    grant = await recovery.verify_challenge(challenge, code, IP)
    change = AsyncMock(side_effect=HTTPException(503, 'Synthetic Auth outage'))
    monkeypatch.setattr(recovery, 'change_password', change)
    response = await state.client.post('/api/v1/auth/password-reset/complete', json={'reset_token': grant, 'password': PASSWORD})
    assert response.status_code == 503
    with pytest.raises(HTTPException):
        await recovery.consume_grant(grant, IP)
