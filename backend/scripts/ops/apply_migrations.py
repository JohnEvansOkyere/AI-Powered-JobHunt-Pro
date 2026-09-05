#!/usr/bin/env python3
"""Apply pipeline-managed PostgreSQL migrations safely.

Migrations 003-018 predate automatic tracking and may already have been
applied manually, so this runner deliberately starts at 019. Each managed
migration must have one outer BEGIN/COMMIT pair; the runner removes that pair
and commits the SQL plus its ledger row atomically.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent
MIGRATIONS_DIR = REPO_DIR / "migrations"
MIN_MANAGED_VERSION = 19
MIGRATION_PATTERN = re.compile(r"^(?P<version>\d{3})_[a-z0-9_]+\.sql$")
LOCK_KEY = 8_611_904_019


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    checksum: str
    sql: str


def _transaction_body(sql: str, path: Path) -> str:
    """Remove the migration's single outer transaction wrapper."""
    lines = sql.splitlines()
    begin_indexes = [index for index, line in enumerate(lines) if line.strip().upper() == "BEGIN;"]
    commit_indexes = [index for index, line in enumerate(lines) if line.strip().upper() == "COMMIT;"]
    if len(begin_indexes) != 1 or len(commit_indexes) != 1:
        raise ValueError(f"{path.name} must contain exactly one outer BEGIN; and COMMIT;")
    begin_index, commit_index = begin_indexes[0], commit_indexes[0]
    if begin_index >= commit_index:
        raise ValueError(f"{path.name} has an invalid transaction wrapper")
    trailing_code = [
        line for line in lines[commit_index + 1 :] if line.strip() and not line.lstrip().startswith("--")
    ]
    if trailing_code:
        raise ValueError(f"{path.name} contains executable SQL after COMMIT;")
    return "\n".join(lines[begin_index + 1 : commit_index]).strip()


def discover_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    migrations: list[Migration] = []
    versions: set[int] = set()
    for path in sorted(directory.glob("*.sql")):
        match = MIGRATION_PATTERN.match(path.name)
        if not match:
            continue
        version = int(match.group("version"))
        if version < MIN_MANAGED_VERSION:
            continue
        if version in versions:
            raise ValueError(f"Duplicate managed migration version: {version:03d}")
        versions.add(version)
        raw_sql = path.read_text(encoding="utf-8")
        body = _transaction_body(raw_sql, path)
        migrations.append(
            Migration(
                version=version,
                name=path.name,
                path=path,
                checksum=hashlib.sha256(raw_sql.encode("utf-8")).hexdigest(),
                sql=body,
            )
        )
    expected = list(range(MIN_MANAGED_VERSION, MIN_MANAGED_VERSION + len(migrations)))
    actual = [migration.version for migration in migrations]
    if actual != expected:
        raise ValueError(
            f"Managed migrations must be contiguous from {MIN_MANAGED_VERSION:03d}; found {actual}"
        )
    return migrations


def _database_url() -> str:
    load_dotenv(BACKEND_DIR / ".env", override=False)
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL is required to apply migrations")
    return value.replace("postgresql+psycopg2://", "postgresql://", 1)


def apply_migrations(migrations: list[Migration], database_url: str) -> int:
    applied_count = 0
    connection = psycopg2.connect(database_url, connect_timeout=15)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS public.schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

        for migration in migrations:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT name, checksum FROM public.schema_migrations WHERE version = %s",
                    (migration.version,),
                )
                existing = cursor.fetchone()
            if existing:
                existing_name, existing_checksum = existing
                if existing_name != migration.name or existing_checksum != migration.checksum:
                    raise RuntimeError(
                        f"Migration {migration.version:03d} was changed after it was applied; "
                        "create a new migration instead"
                    )
                print(f"skip  {migration.name} (already applied)")
                continue

            connection.autocommit = False
            try:
                with connection.cursor() as cursor:
                    cursor.execute(migration.sql)
                    cursor.execute(
                        """
                        INSERT INTO public.schema_migrations (version, name, checksum)
                        VALUES (%s, %s, %s)
                        """,
                        (migration.version, migration.name, migration.checksum),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.autocommit = True
            applied_count += 1
            print(f"apply {migration.name}")
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))
        finally:
            connection.close()
    return applied_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply VeloxaHire database migrations")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate managed migration files without connecting to PostgreSQL",
    )
    args = parser.parse_args()
    try:
        migrations = discover_migrations()
        if not migrations:
            raise RuntimeError(f"No migrations found at or after {MIN_MANAGED_VERSION:03d}")
        if args.check:
            for migration in migrations:
                print(f"valid {migration.name} {migration.checksum[:12]}")
            return 0
        applied = apply_migrations(migrations, _database_url())
        print(f"Migration check complete: {applied} applied, {len(migrations) - applied} unchanged")
        return 0
    except Exception as exc:
        print(f"Migration failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
