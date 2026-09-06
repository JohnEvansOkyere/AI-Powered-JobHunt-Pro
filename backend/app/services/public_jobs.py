"""Shared public job visibility. History is retained; known-closed jobs are hidden."""

from datetime import datetime, timezone

from sqlalchemy import or_

from app.models.job import Job


def active_job_filters():
    return (
        Job.processing_status != "archived",
        or_(Job.publication_status.is_(None), Job.publication_status == "published"),
        or_(Job.application_deadline.is_(None), Job.application_deadline > datetime.now(timezone.utc)),
    )
