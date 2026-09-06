"""Errors must stay safe for browser clients even with DEBUG enabled."""
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import DatabaseError
from app.middleware import error_handler as errors
from app.middleware.request_logger import RequestLoggingMiddleware

PRIVATE = "synthetic-secret database relation users missing /srv/private.py"


@pytest.fixture(params=[True, False])
def error_client(request, monkeypatch):
    monkeypatch.setattr(errors.settings, 'DEBUG', request.param)
    app = FastAPI()
    app.add_middleware(errors.ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_exception_handler(StarletteHTTPException, errors.http_exception_handler)
    app.add_exception_handler(RequestValidationError, errors.validation_exception_handler)

    @app.get('/fail/{kind}')
    def fail(kind: str):
        if kind == 'http':
            raise HTTPException(503, PRIVATE, headers={'Retry-After': '90'})
        if kind == 'app':
            raise DatabaseError(PRIVATE, details={'password': PRIVATE})
        if kind == 'database':
            raise OperationalError('SELECT secret', {}, Exception(PRIVATE))
        if kind == 'conflict':
            raise IntegrityError('INSERT secret', {}, Exception(PRIVATE))
        if kind == 'value':
            raise ValueError(PRIVATE)
        if kind == 'auth':
            raise HTTPException(401, 'Invalid authentication credentials', headers={'WWW-Authenticate': 'Bearer'})
        if kind == 'reset':
            raise HTTPException(400, 'This reset has expired or was already used. Request a new code.')
        raise RuntimeError(PRIVATE)

    class Payload(BaseModel):
        password: str = Field(min_length=100)

    @app.post('/validate')
    def validate(payload: Payload):
        return {}

    return TestClient(app)


@pytest.mark.parametrize('kind,status', [('http', 503), ('app', 500), ('database', 503),
                                       ('conflict', 409), ('value', 400), ('unexpected', 500)])
def test_internal_errors_are_not_returned(error_client, kind, status):
    response = error_client.get('/fail/' + kind)
    assert response.status_code == status
    for private in [PRIVATE, 'SELECT', 'INSERT', 'OperationalError', 'RuntimeError', 'password']:
        assert private not in response.text
    uuid.UUID(response.headers['X-Request-ID'])
    if 'error' in response.json():
        assert response.json()['error']['request_id'] == response.headers['X-Request-ID']
        assert response.json()['error']['details'] == {}
    if kind == 'http':
        assert response.headers['Retry-After'] == '90'
        assert response.headers['Cache-Control'] == 'no-store'


def test_auth_and_recovery_semantics_preserved(error_client):
    response = error_client.get('/fail/auth')
    assert response.status_code == 401
    assert response.headers['WWW-Authenticate'] == 'Bearer'
    assert response.json()['detail'] == 'Invalid authentication credentials'
    response = error_client.get('/fail/reset')
    assert response.status_code == 400
    assert 'Request a new code.' in response.json()['detail']


def test_validation_never_logs_or_returns_inputs(error_client, monkeypatch):
    log = MagicMock()
    monkeypatch.setattr(errors, 'logger', log)
    response = error_client.post('/validate', json={'password': PRIVATE})
    assert response.status_code == 422
    assert PRIVATE not in response.text
    assert PRIVATE not in str(log.mock_calls)
    assert log.warning.called


def test_cv_response_hides_stored_parser_diagnostics():
    from datetime import datetime, timezone
    from app.api.v1.endpoints.cvs import CVDetailResponse
    cv = CVDetailResponse(
        id=uuid.uuid4(), user_id=uuid.uuid4(), file_name='test.pdf', file_path='synthetic/test.pdf',
        file_size=100, file_type='pdf', mime_type='application/pdf', parsing_status='failed',
        parsing_error=PRIVATE, is_active=True, created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc), parsed_content=None, raw_text=None,
    )
    assert PRIVATE not in cv.model_dump_json()
    assert 'clear PDF or Word document' in cv.model_dump()['parsing_error']
    assert cv.parsing_error == PRIVATE  # diagnostics remain available internally


def test_real_app_adds_cors_to_middleware_errors(monkeypatch):
    from app.main import create_application
    monkeypatch.setattr(errors.settings, 'DEBUG', True)
    monkeypatch.setattr(errors.settings, 'CORS_ORIGINS', ['https://synthetic.test'])
    app = create_application()

    @app.get('/test-error')
    def fail():
        raise RuntimeError(PRIVATE)

    response = TestClient(app).get('/test-error', headers={'Origin': 'https://synthetic.test'})
    assert response.status_code == 500
    assert PRIVATE not in response.text
    assert response.headers['Access-Control-Allow-Origin'] == 'https://synthetic.test'
    assert 'X-Request-ID' in response.headers['Access-Control-Expose-Headers']
    uuid.UUID(response.headers['X-Request-ID'])
