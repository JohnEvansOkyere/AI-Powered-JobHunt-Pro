from pathlib import Path

import pytest

from scripts.ops import apply_migrations as runner
from scripts.ops.apply_migrations import (
    Migration,
    MIN_MANAGED_VERSION,
    _transaction_body,
    discover_migrations,
)


def test_repository_migrations_are_valid_and_contiguous():
    migrations = discover_migrations()
    assert migrations[0].version == MIN_MANAGED_VERSION
    assert [migration.version for migration in migrations] == list(
        range(MIN_MANAGED_VERSION, MIN_MANAGED_VERSION + len(migrations))
    )
    assert migrations[0].name == "019_add_editable_cv_generations.sql"
    assert "CREATE TABLE IF NOT EXISTS cv_generations" in migrations[0].sql
    assert "BEGIN;" not in migrations[0].sql
    assert "COMMIT;" not in migrations[0].sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1;",
        "BEGIN;\nSELECT 1;",
        "COMMIT;\nSELECT 1;",
        "BEGIN;\nCOMMIT;\nSELECT 1;",
        "BEGIN;\nBEGIN;\nCOMMIT;",
    ],
)
def test_transaction_wrapper_rejects_unsafe_shapes(sql: str):
    with pytest.raises(ValueError):
        _transaction_body(sql, Path("019_bad.sql"))


def test_discovery_rejects_a_gap(tmp_path: Path):
    (tmp_path / "019_first.sql").write_text("BEGIN;\nSELECT 1;\nCOMMIT;", encoding="utf-8")
    (tmp_path / "021_gap.sql").write_text("BEGIN;\nSELECT 1;\nCOMMIT;", encoding="utf-8")
    with pytest.raises(ValueError, match="contiguous"):
        discover_migrations(tmp_path)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, sql, params=None):
        self.connection.calls.append((sql, params))

    def fetchone(self):
        return self.connection.ledger_row


class FakeConnection:
    def __init__(self, ledger_row=None):
        self.autocommit = False
        self.ledger_row = ledger_row
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def sample_migration() -> Migration:
    return Migration(19, "019_sample.sql", Path("019_sample.sql"), "abc123", "SELECT 1")


def test_apply_commits_sql_and_ledger_before_unlock(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(runner.psycopg2, "connect", lambda *_args, **_kwargs: connection)

    assert runner.apply_migrations([sample_migration()], "postgresql://example") == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert any("INSERT INTO public.schema_migrations" in call[0] for call in connection.calls)
    assert "pg_advisory_unlock" in connection.calls[-1][0]
    assert connection.closed is True


def test_apply_skips_matching_ledger_entry(monkeypatch):
    migration = sample_migration()
    connection = FakeConnection((migration.name, migration.checksum))
    monkeypatch.setattr(runner.psycopg2, "connect", lambda *_args, **_kwargs: connection)

    assert runner.apply_migrations([migration], "postgresql://example") == 0
    assert connection.commits == 0
    assert not any("INSERT INTO public.schema_migrations" in call[0] for call in connection.calls)
