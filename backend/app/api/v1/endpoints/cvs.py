"""
CV Management API Endpoints

Handles CV upload, parsing, retrieval, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from pathlib import Path

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user
from app.core.supabase_client import get_supabase_service_client
from app.core.config import settings
from app.core.logging import get_logger
from app.models.cv import CV
from app.services.cv_parser import CVParser
from pydantic import BaseModel, field_serializer

logger = get_logger(__name__)

router = APIRouter()
cv_parser = CVParser()


# Pydantic models for request/response
class CVResponse(BaseModel):
    """CV response model."""
    
    id: uuid.UUID
    user_id: uuid.UUID
    file_name: str
    file_path: str
    file_size: Optional[int]
    file_type: Optional[str]
    mime_type: Optional[str]
    parsing_status: str
    parsing_error: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO format string."""
        return dt.isoformat() if dt else None
    
    class Config:
        from_attributes = True


class CVDetailResponse(CVResponse):
    """CV detail response with parsed content."""
    
    parsed_content: Optional[dict]
    raw_text: Optional[str]
    
    class Config:
        from_attributes = True


@router.post("/upload", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a CV file (PDF or DOCX).
    
    - Validates file type and size
    - Uploads to Supabase Storage
    - Creates CV record in database
    - Starts async parsing process
    """
    # Log request details
    logger.info(f"CV upload request received - filename: {file.filename if file.filename else 'None'}, content_type: {file.content_type if file.content_type else 'None'}")
    
    # Validate filename exists
    if not file.filename:
        error_msg = "File must have a filename"
        logger.error(f"Upload attempt with no filename - content_type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Validate file type - check extension
    allowed_extensions = [".pdf", ".docx"]
    
    # Get file extension - handle various cases
    file_extension = None
    if file.filename:
        # Try to get extension from filename
        filename_lower = file.filename.lower()
        if filename_lower.endswith('.pdf'):
            file_extension = '.pdf'
        elif filename_lower.endswith('.docx'):
            file_extension = '.docx'
        elif filename_lower.endswith('.doc'):
            # .doc files not supported
            logger.warning(f"Unsupported .doc file: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=".doc files are not supported. Please convert to .docx or .pdf"
            )
        else:
            # Try Path method as fallback
            path_suffix = Path(file.filename).suffix.lower()
            if path_suffix in allowed_extensions:
                file_extension = path_suffix
            else:
                # No valid extension found
                logger.warning(f"No valid extension found for file: {file.filename}, path_suffix: {path_suffix}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File '{file.filename}' has no valid extension. Allowed extensions: {', '.join(allowed_extensions)}"
                )
    else:
        logger.error("File has no filename")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename"
        )
    
    logger.info(f"File details - name: {file.filename}, extension: {file_extension}, content_type: {file.content_type}")
    
    if not file_extension or file_extension not in allowed_extensions:
        logger.warning(f"Invalid file extension: '{file_extension}' for file: {file.filename}. Allowed: {allowed_extensions}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. File '{file.filename}' has extension '{file_extension}'. Allowed extensions: {', '.join(allowed_extensions)}"
        )
    
    # Read file content (can only be read once)
    file_content = await file.read()
    file_size = len(file_content)
    max_size = 10 * 1024 * 1024  # 10MB
    
    logger.info(f"File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
    
    if file_size > max_size:
        logger.warning(f"File too large: {file_size} bytes")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({file_size / 1024 / 1024:.2f} MB). Maximum size: 10MB"
        )
    
    if file_size == 0:
        logger.warning("Empty file uploaded")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    try:
        # Determine file type
        file_type = "pdf" if file_extension == ".pdf" else "docx"
        mime_type = file.content_type or (
            "application/pdf" if file_type == "pdf" 
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        # Generate unique file path
        user_id_str = str(current_user["id"])
        file_id = str(uuid.uuid4())
        file_path = f"{user_id_str}/{file_id}{file_extension}"
        
        # Upload to Supabase Storage
        supabase = get_supabase_service_client()
        try:
            storage_response = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": mime_type, "upsert": False}
            )
            
            # Supabase upload() returns an UploadResponse object
            # If upload fails, it typically raises an exception or returns response with error
            # Check for errors - handle both object and dict responses
            error_msg = None
            if hasattr(storage_response, 'error') and storage_response.error:
                error_msg = str(storage_response.error)
            elif isinstance(storage_response, dict) and storage_response.get("error"):
                error_msg = storage_response.get("error")
            
            if error_msg:
                logger.error(f"Supabase Storage upload failed: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file to storage: {error_msg}"
                )
            
            logger.info(f"File uploaded successfully to Supabase Storage: {file_path}")
        except Exception as storage_error:
            logger.error(f"Supabase Storage upload exception: {storage_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to storage: {str(storage_error)}"
            )
        
        # Convert user_id to UUID if it's a string
        user_id = current_user["id"]
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        
        # Deactivate existing CVs for this user
        db.query(CV).filter(
            and_(CV.user_id == user_id, CV.is_active == True)
        ).update({"is_active": False})
        
        # Create CV record
        cv = CV(
            user_id=user_id,
            file_name=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            parsing_status="pending",
            is_active=True,
        )
        
        db.add(cv)
        db.commit()
        db.refresh(cv)
        
        # Start async parsing (in production, use Celery task)
        # For now, parse synchronously
        try:
            logger.info(f"Starting CV parsing for CV {cv.id}")
            cv.parsing_status = "processing"
            db.commit()
            
            parse_result = await cv_parser.parse_cv(file_content, file_type)
            
            cv.raw_text = parse_result["raw_text"]
            cv.parsed_content = parse_result["parsed_content"]
            cv.parsing_status = "completed"
            cv.parsing_error = None
            
            db.commit()
            db.refresh(cv)
            
            logger.info(f"CV parsing completed for CV {cv.id}")
        except Exception as parse_error:
            logger.error(f"CV parsing failed for CV {cv.id}: {parse_error}")
            cv.parsing_status = "failed"
            cv.parsing_error = str(parse_error)
            db.commit()
        
        return CVResponse.from_orm(cv)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading CV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload CV: {str(e)}"
        )


@router.get("/", response_model=List[CVResponse])
def list_cvs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all CVs for the current user."""
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    cvs = db.query(CV).filter(CV.user_id == user_id).order_by(CV.created_at.desc()).all()
    return [CVResponse.from_orm(cv) for cv in cvs]


@router.get("/active", response_model=Optional[CVDetailResponse])
def get_active_cv(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the active CV for the current user with parsed content."""
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    cv = db.query(CV).filter(
        and_(CV.user_id == user_id, CV.is_active == True)
    ).first()
    
    if not cv:
        return None
    
    return CVDetailResponse.from_orm(cv)


@router.get("/{cv_id}", response_model=CVDetailResponse)
def get_cv(
    cv_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific CV by ID with parsed content."""
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    cv = db.query(CV).filter(
        and_(CV.id == cv_id, CV.user_id == user_id)
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    return CVDetailResponse.from_orm(cv)


@router.post("/{cv_id}/activate", response_model=CVResponse)
def activate_cv(
    cv_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a CV as active (deactivates others)."""
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    cv = db.query(CV).filter(
        and_(CV.id == cv_id, CV.user_id == user_id)
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    # Deactivate all other CVs
    db.query(CV).filter(
        and_(CV.user_id == user_id, CV.is_active == True)
    ).update({"is_active": False})
    
    # Activate this CV
    cv.is_active = True
    db.commit()
    db.refresh(cv)
    
    return CVResponse.from_orm(cv)


@router.delete("/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cv(
    cv_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a CV and its file from storage."""
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    cv = db.query(CV).filter(
        and_(CV.id == cv_id, CV.user_id == user_id)
    ).first()
    
    if not cv:
        logger.warning(f"CV not found: cv_id={cv_id}, user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    try:
        # Delete from Supabase Storage
        supabase = get_supabase_service_client()
        supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([cv.file_path])
    except Exception as e:
        logger.warning(f"Failed to delete file from storage: {e}")
    
    # Delete from database
    db.delete(cv)
    db.commit()
    
    return None


@router.get("/{cv_id}/download-url")
def get_download_url(
    cv_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a signed URL to download the CV file."""
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    cv = db.query(CV).filter(
        and_(CV.id == cv_id, CV.user_id == user_id)
    ).first()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    try:
        supabase = get_supabase_service_client()
        # Generate signed URL (valid for 1 hour)
        url_response = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).create_signed_url(
            path=cv.file_path,
            expires_in=3600
        )
        
        # Handle both object and dict responses
        error_msg = None
        if hasattr(url_response, 'error') and url_response.error:
            error_msg = str(url_response.error)
        elif isinstance(url_response, dict) and url_response.get("error"):
            error_msg = url_response.get("error")
        
        if error_msg:
            logger.error(f"Supabase Storage signed URL generation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )

        # Get signed URL from response
        signed_url = None
        if hasattr(url_response, 'signedURL'):
            signed_url = url_response.signedURL
        elif isinstance(url_response, dict):
            signed_url = url_response.get("signedURL")
        
        if not signed_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get download URL from response"
            )

        return {"download_url": signed_url}
    except Exception as e:
        logger.error(f"Error generating download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )

