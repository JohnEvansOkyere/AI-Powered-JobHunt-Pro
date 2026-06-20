"""Tests for account export/deletion privacy workflows."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import users
from app.models.application import Application
from app.models.cv import CV
from app.models.job import Job


class _FakeQuery:
    def __init__(self, *, rows=None, first=None, delete_count=0, update_count=0):
        self.rows = rows or []
        self.first_value = first
        self.delete_count = delete_count
        self.update_count = update_count
        self.deleted = False
        self.updated_with = None

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.first_value

    def delete(self, synchronize_session=False):
        self.deleted = True
        return self.delete_count

    def update(self, values, synchronize_session=False):
        self.updated_with = values
        return self.update_count


class _FakeSession:
    def __init__(self, query_map):
        self.query_map = query_map
        self.committed = False
        self.rolled_back = False

    def query(self, model):
        return self.query_map.get(model, _FakeQuery())

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_current_user_uuid_rejects_invalid_user_id():
    with pytest.raises(HTTPException) as exc:
        users._current_user_uuid({"id": "not-a-uuid"})

    assert exc.value.status_code == 400


def test_serialize_model_includes_columns_without_relationships():
    user_id = uuid.uuid4()
    application = Application(user_id=user_id, job_id=uuid.uuid4(), status="saved")

    serialized = users._serialize_model(application)

    assert serialized["user_id"] == str(user_id)
    assert serialized["status"] == "saved"
    assert "job" not in serialized


@pytest.mark.asyncio
async def test_delete_my_account_detaches_external_jobs_instead_of_deleting(monkeypatch):
    user_id = uuid.uuid4()
    cv = CV(user_id=user_id, file_name="cv.pdf", file_path=f"{user_id}/cv.pdf")
    job_query = _FakeQuery(update_count=2)
    db = _FakeSession(
        {
            CV: _FakeQuery(rows=[cv], delete_count=1),
            Application: _FakeQuery(delete_count=3),
            Job: job_query,
        }
    )

    storage_bucket = MagicMock()
    storage_bucket.remove.return_value = {"error": None}
    storage = MagicMock()
    storage.from_.return_value = storage_bucket
    auth_admin = MagicMock()
    service_client = SimpleNamespace(
        storage=storage,
        auth=SimpleNamespace(admin=auth_admin),
    )
    monkeypatch.setattr(users, "get_supabase_service_client", lambda: service_client)

    response = await users.delete_my_account({"id": str(user_id)}, db)

    assert response["status"] == "deleted"
    assert response["deleted_counts"]["external_jobs_detached_from_user"] == 2
    assert job_query.updated_with == {"added_by_user_id": None}
    assert db.committed is True
    storage_bucket.remove.assert_called_once_with([f"{user_id}/cv.pdf"])
    auth_admin.delete_user.assert_called_once_with(str(user_id))
