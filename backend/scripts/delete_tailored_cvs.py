"""Delete legacy tailored-CV artifacts from Supabase Storage.

Context
-------
V2 of the product removes the "tailor my CV for this role" feature
(see ``docs/RECOMMENDATIONS_V2_PLAN.md`` §4 and migration 007). Before v2,
every call to ``generate_tailored_cv`` uploaded a generated DOCX/PDF under
``tailored-cvs/<user_id>/...`` inside the ``cvs`` Supabase bucket and stored
the path on ``applications.tailored_cv_path``. Migration 007 drops that
column, so this script reclaims the underlying storage so we stop paying
for files we can no longer reference.

Safety
------
*   Defaults to dry-run. Pass ``--apply`` to actually delete.
*   Only touches objects under the ``tailored-cvs/`` prefix — regular user
    CVs live under ``<user_id>/...`` and are left alone.
*   Uses the service-role client (required to bypass RLS on Storage),
    so run this from a trusted environment with ``SUPABASE_SERVICE_KEY``
    available. Never commit its output.

Usage
-----
    cd backend
    venv/bin/python scripts/delete_tailored_cvs.py           # dry-run
    venv/bin/python scripts/delete_tailored_cvs.py --apply   # destructive
    venv/bin/python scripts/delete_tailored_cvs.py --apply --batch-size 50

Exit codes: 0 on success, 1 on any error.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, List

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import settings  # noqa: E402
from app.core.logging import get_logger  # noqa: E402
from app.core.supabase_client import get_supabase_service_client  # noqa: E402

logger = get_logger(__name__)

TAILORED_PREFIX = "tailored-cvs"
PAGE_SIZE = 100  # Supabase Storage list() cap per call


def _walk_tailored_paths(bucket) -> Iterable[str]:
    """Yield every object path under ``tailored-cvs/`` recursively.

    Supabase's Storage `list` is not recursive, so we do a DFS over the
    folder tree. Empty-folder markers (objects without ``name``) are
    skipped; true files always have a non-empty ``name``.
    """
    stack: List[str] = [TAILORED_PREFIX]
    while stack:
        prefix = stack.pop()
        offset = 0
        while True:
            try:
                entries = bucket.list(
                    path=prefix,
                    options={"limit": PAGE_SIZE, "offset": offset},
                )
            except Exception as exc:  # pragma: no cover - network path
                logger.error("Storage list failed for prefix=%s: %s", prefix, exc)
                raise

            if not entries:
                break

            for entry in entries:
                name = entry.get("name") if isinstance(entry, dict) else None
                if not name:
                    continue
                full_path = f"{prefix}/{name}"
                # Folders in Supabase Storage have metadata == None.
                metadata = entry.get("metadata") if isinstance(entry, dict) else None
                if metadata is None:
                    stack.append(full_path)
                else:
                    yield full_path

            if len(entries) < PAGE_SIZE:
                break
            offset += PAGE_SIZE


def _chunk(items: List[str], size: int) -> Iterable[List[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete files. Without this flag the script only lists them.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="How many objects to delete per Storage API call (default: 100).",
    )
    parser.add_argument(
        "--bucket",
        default=settings.SUPABASE_STORAGE_BUCKET,
        help="Storage bucket that held tailored CVs (defaults to settings.SUPABASE_STORAGE_BUCKET).",
    )
    args = parser.parse_args()

    supabase = get_supabase_service_client()
    bucket = supabase.storage.from_(args.bucket)

    logger.info(
        "Scanning bucket=%s prefix=%s (dry_run=%s)",
        args.bucket,
        TAILORED_PREFIX,
        not args.apply,
    )

    paths: List[str] = list(_walk_tailored_paths(bucket))
    total = len(paths)
    if total == 0:
        logger.info("No tailored-cv artifacts found. Nothing to do.")
        return 0

    logger.info("Found %d tailored-cv object(s).", total)
    if not args.apply:
        sample = paths[:10]
        for p in sample:
            logger.info("  [dry-run] would delete: %s", p)
        if total > len(sample):
            logger.info("  [dry-run] ... and %d more", total - len(sample))
        logger.info("Re-run with --apply to delete these %d files.", total)
        return 0

    deleted = 0
    for batch in _chunk(paths, max(1, args.batch_size)):
        try:
            bucket.remove(batch)
        except Exception as exc:  # pragma: no cover - network path
            logger.error("Failed to delete batch of %d (first=%s): %s", len(batch), batch[0], exc)
            return 1
        deleted += len(batch)
        logger.info("Deleted %d / %d", deleted, total)

    logger.info("Done. Removed %d tailored-cv artifact(s) from %s.", deleted, args.bucket)
    return 0


if __name__ == "__main__":
    sys.exit(main())
