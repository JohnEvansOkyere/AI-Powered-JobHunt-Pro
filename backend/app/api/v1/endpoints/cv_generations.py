"""Authenticated, owner-scoped tailored CV generation and editing API."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import CV_GENERATION_RATE_LIMIT, enforce_rate_limit
from app.models.cv import CV
from app.models.cv_generation import CVGeneration, CVGenerationRevision
from app.models.job import Job
from app.services.cv_document import render_cv_docx
from app.services.cv_tailoring import (
    CVContent,
    CVTailoringError,
    PROMPT_VERSION,
    content_hash,
    generate_tailored_cv,
)

router = APIRouter()


class GenerateCVRequest(BaseModel):
    job_id: uuid.UUID
    source_cv_id: uuid.UUID | None = None
    regenerate: bool = False


class UpdateCVRequest(BaseModel):
    content: CVContent
    expected_revision: int = Field(ge=1)


class GenerationResponse(BaseModel):
    id: uuid.UUID
    source_cv_id: uuid.UUID
    job_id: uuid.UUID
    revision: int
    content: CVContent
    validation_warnings: list[str]
    prompt_version: str
    created_at: datetime
    updated_at: datetime
    job_title: str
    company: str


class RevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revision: int
    change_source: str
    created_at: datetime


def _user_id(current_user: dict) -> uuid.UUID:
    try:
        return uuid.UUID(str(current_user["id"]))
    except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - dependency guarantees this
        raise HTTPException(status_code=401, detail="Invalid authenticated user.") from exc


def _owned_generation(
    db: Session,
    generation_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> CVGeneration:
    query = (
        db.query(CVGeneration)
        .filter(CVGeneration.id == generation_id, CVGeneration.user_id == user_id)
    )
    if for_update:
        query = query.with_for_update()
    generation = query.first()
    if not generation:
        # Do not reveal whether another user's private draft exists.
        raise HTTPException(status_code=404, detail="Tailored CV not found.")
    return generation


def _response(generation: CVGeneration, job: Job | None = None) -> dict:
    job = job or generation.job
    return {
        "id": generation.id,
        "source_cv_id": generation.source_cv_id,
        "job_id": generation.job_id,
        "revision": generation.revision,
        "content": generation.content,
        "validation_warnings": generation.validation_warnings or [],
        "prompt_version": generation.prompt_version,
        "created_at": generation.created_at,
        "updated_at": generation.updated_at,
        "job_title": job.title,
        "company": job.company,
    }


@router.post("", response_model=GenerationResponse, status_code=status.HTTP_201_CREATED)
async def create_generation(
    payload: GenerateCVRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = _user_id(current_user)

    cv_query = db.query(CV).filter(
        CV.user_id == user_id,
        CV.parsing_status == "completed",
        CV.parsed_content.isnot(None),
    )
    if payload.source_cv_id:
        cv_query = cv_query.filter(CV.id == payload.source_cv_id)
    else:
        cv_query = cv_query.filter(CV.is_active.is_(True)).order_by(CV.updated_at.desc())
    source_cv = cv_query.first()
    if not source_cv:
        raise HTTPException(
            status_code=400,
            detail="Upload and finish parsing a CV before generating a tailored version.",
        )

    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    source_digest = content_hash(source_cv.parsed_content)
    if not payload.regenerate:
        existing = (
            db.query(CVGeneration)
            .filter(
                CVGeneration.user_id == user_id,
                CVGeneration.source_cv_id == source_cv.id,
                CVGeneration.job_id == job.id,
                CVGeneration.source_content_hash == source_digest,
            )
            .order_by(CVGeneration.updated_at.desc())
            .first()
        )
        if existing:
            return _response(existing, job)

    # Reopening an existing draft is free; only a real model call consumes the
    # per-user generation allowance.
    await enforce_rate_limit(request, CV_GENERATION_RATE_LIMIT, subject=str(user_id))

    try:
        tailored, warnings = await generate_tailored_cv(
            source_cv.parsed_content,
            {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "job_type": job.job_type,
                "remote_type": job.remote_type,
                "description": job.description,
                "requirements": job.requirements,
            },
            str(user_id),
        )
    except CVTailoringError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    generation = CVGeneration(
        user_id=user_id,
        source_cv_id=source_cv.id,
        job_id=job.id,
        content=tailored,
        ai_content=tailored,
        source_content_hash=source_digest,
        revision=1,
        ai_provider="model-router",
        prompt_version=PROMPT_VERSION,
        validation_warnings=warnings,
    )
    db.add(generation)
    db.flush()
    db.add(
        CVGenerationRevision(
            generation_id=generation.id,
            revision=1,
            content=tailored,
            change_source="ai",
        )
    )
    db.commit()
    db.refresh(generation)
    return _response(generation, job)


@router.get("", response_model=list[GenerationResponse])
def list_generations(
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    user_id = _user_id(current_user)
    rows = (
        db.query(CVGeneration)
        .filter(CVGeneration.user_id == user_id)
        .order_by(CVGeneration.updated_at.desc())
        .limit(100)
        .all()
    )
    return [_response(row) for row in rows]


@router.get("/{generation_id}", response_model=GenerationResponse)
def get_generation(
    generation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _response(_owned_generation(db, generation_id, _user_id(current_user)))


@router.patch("/{generation_id}", response_model=GenerationResponse)
def update_generation(
    generation_id: uuid.UUID,
    payload: UpdateCVRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = _user_id(current_user)
    generation = (
        db.query(CVGeneration)
        .filter(CVGeneration.id == generation_id, CVGeneration.user_id == user_id)
        .with_for_update()
        .first()
    )
    if not generation:
        raise HTTPException(status_code=404, detail="Tailored CV not found.")
    if generation.revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail="This CV changed in another session. Reload it before saving again.",
        )
    generation.revision += 1
    generation.content = payload.content.model_dump()
    db.add(
        CVGenerationRevision(
            generation_id=generation.id,
            revision=generation.revision,
            content=generation.content,
            change_source="user",
        )
    )
    db.commit()
    db.refresh(generation)
    return _response(generation)


@router.get("/{generation_id}/revisions", response_model=list[RevisionResponse])
def list_revisions(
    generation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    generation = _owned_generation(db, generation_id, _user_id(current_user))
    return (
        db.query(CVGenerationRevision)
        .filter(CVGenerationRevision.generation_id == generation.id)
        .order_by(CVGenerationRevision.revision.desc())
        .limit(50)
        .all()
    )


def _replace_content(
    db: Session, generation: CVGeneration, content: dict, change_source: str
) -> CVGeneration:
    generation.revision += 1
    generation.content = content
    db.add(
        CVGenerationRevision(
            generation_id=generation.id,
            revision=generation.revision,
            content=content,
            change_source=change_source,
        )
    )
    db.commit()
    db.refresh(generation)
    return generation


@router.post("/{generation_id}/reset", response_model=GenerationResponse)
def reset_generation(
    generation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    generation = _owned_generation(db, generation_id, _user_id(current_user), for_update=True)
    return _response(_replace_content(db, generation, generation.ai_content, "reset"))


@router.post("/{generation_id}/restore/{revision}", response_model=GenerationResponse)
def restore_revision(
    generation_id: uuid.UUID,
    revision: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    generation = _owned_generation(db, generation_id, _user_id(current_user), for_update=True)
    selected = (
        db.query(CVGenerationRevision)
        .filter(
            CVGenerationRevision.generation_id == generation.id,
            CVGenerationRevision.revision == revision,
        )
        .first()
    )
    if not selected:
        raise HTTPException(status_code=404, detail="CV revision not found.")
    return _response(_replace_content(db, generation, selected.content, "restore"))


@router.get("/{generation_id}/download.docx")
def download_docx(
    generation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    generation = _owned_generation(db, generation_id, _user_id(current_user))
    filename_base = re.sub(r"[^a-zA-Z0-9_-]+", "-", f"{generation.job.title}-{generation.job.company}")
    return Response(
        content=render_cv_docx(generation.content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename_base[:100]}-CV.docx"'},
    )
