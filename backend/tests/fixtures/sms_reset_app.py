"""Local-only browser fixture: real reset routes/Redis; fake DB/Auth/SMS."""
import os
import uuid

if os.environ.get('PASSWORD_RESET_BROWSER_FIXTURE') != '1':
    raise RuntimeError('This synthetic API is for explicit local browser tests only.')
from types import SimpleNamespace
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from app.api.v1.endpoints.password_reset import router
from app.core.database import get_db
from app.services import password_reset as recovery

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:3027'], allow_methods=['*'], allow_headers=['*'], expose_headers=['Retry-After'])
app.include_router(router, prefix='/api/v1/auth')
redis = Redis.from_url('redis://127.0.0.1:16389/0', decode_responses=True)
recovery.PREFIX = 'browser:{password-reset}:'
recovery.settings.AUTH_SUPABASE_SERVICE_KEY = 'synthetic-admin-key'
user = dict(id='11111111-1111-4111-8111-111111111111', email='candidate@example.com', phone='233241234567', phone_confirmed_at='2026-09-06T00:00:00Z', updated_at='2026-09-06T00:00:00Z')
state = {'sent': 0, 'changed': 0, 'code': '', 'password_matches': False}
async def redis_client(): return redis
async def auth_user(_): return user
async def send_auth_code(**kwargs):
    state['sent'] += 1
    state['code'] = kwargs['otp']
async def change_password(uid, password):
    assert uid == user['id']
    state['changed'] += 1
    state['password_matches'] = password == 'Synthetic-new-password-123'
    user['updated_at'] = '2026-09-06T12:00:00Z'
recovery.get_async_redis = redis_client
recovery.auth_user = auth_user
recovery.change_password = change_password
recovery.sms_providers = lambda: [('synthetic', SimpleNamespace(send_auth_code=send_auth_code))]
db = MagicMock()
db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=uuid.UUID(user['id']), is_active=True)
app.dependency_overrides[get_db] = lambda: db

@app.get('/test/state')
async def get_state(): return state

@app.post('/test/clear')
async def clear():
    keys = [key async for key in redis.scan_iter(match=recovery.PREFIX + '*')]
    if keys: await redis.delete(*keys)
    state.update(sent=0, changed=0, code='', password_matches=False)
    user['updated_at'] = '2026-09-06T00:00:00Z'
    return {'ok': True}

@app.post('/api/v1/analytics/events')
async def analytics(): return {'ok': True}
