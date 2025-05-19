from typing import Any, List, Optional, Dict, Annotated
import uuid
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel import select, desc, update
import logging

from app.api.deps import CurrentUser, SessionDep, get_user_with_permission
from app.core.models.document import Document, DocumentChunk
from app.core.config.constants import DocumentSourceType, DocumentStatus, ChunkingStrategy
from app.core.config.settings import settings
from app.core.models.user import User
from app.core.services.s3 import s3_service
from app.core.services.document_processor import document_processor

router = APIRouter()

# Permission-based dependencies
def require_document_upload_permission(current_user: Annotated[User, Depends()]) -> User:
    return get_user_with_permission("documents:create")(current_user)

def require_document_delete_permission(current_user: Annotated[User, Depends()]) -> User:
    return get_user_with_permission("documents:delete")(current_user)

def require_document_read_permission(current_user: Annotated[User, Depends()]) -> User:
    return get_user_with_permission("documents:read")(current_user)


@router.get("/", response_model=List[Document])
async def list_documents(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    session: SessionDep,
    skip: int = 0, 
    limit: int = 100,
    status: Optional[DocumentStatus] = None,
    source_type: Optional[DocumentSourceType] = None,
) -> Any:
    """List all documents with optional filtering"""
    query = select(Document).offset(skip).limit(limit).order_by(desc(Document.created_at))
    
    if status:
        query = query.where(Document.status == status)
    
    if source_type:
        query = query.where(Document.source_type == source_type)
        
    documents = session.exec(query).all()
    return documents


@router.get("/{document_id}", response_model=Document)
async def get_document(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """Get a specific document by ID"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


async def process_document_async(
    document_id: uuid.UUID,
    session: SessionDep,
) -> None:
    """
    Async background task to process a document
    
    This will:
    1. Download the document from S3
    2. Extract text using Docling
    3. Create chunks based on the configured strategy
    4. Update document status
    """
    # Get document
    document = session.get(Document, str(document_id))
    if not document:
        return
    
    try:
        # Process document with Docling
        await document_processor.process_document(document, session)
    except Exception as e:
        # Log the error and update status
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing document {document_id}: {e}")
        document.status = DocumentStatus.FAILED
        document.updated_at = datetime.now(timezone.utc)
        session.add(document)
        session.commit()


@router.post("/", response_model=Document)
async def upload_document(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_document_upload_permission)],
    session: SessionDep,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    source_type: DocumentSourceType = Form(DocumentSourceType.PDF),
    source_name: Optional[str] = Form(None),
) -> Any:
    """Upload a new document to S3 and add it to the database"""
    
    # Validate file content type
    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file.content_type}. Allowed types: {settings.ALLOWED_DOCUMENT_TYPES}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE} bytes"
        )
    
    # Generate S3 key for the document
    document_id = uuid.uuid4()
    s3_key = f"documents/{document_id}/{file.filename}"
    
    # Create document record with pending status
    document = Document(
        id=str(document_id),
        filename=file.filename,
        title=title or file.filename,
        source_type=source_type,
        source_name=source_name,
        file_path=s3_key,
        content_type=file.content_type,
        file_size=len(content),
        status=DocumentStatus.PENDING,
    )
    
    # Set metadata using the proper property
    document.metadata_dict = {
        "uploaded_by": str(current_user.id),
        "original_filename": file.filename
    }
    
    # Upload to S3
    file.file.seek(0)  # Reset file pointer to beginning
    upload_success = s3_service.upload_file(
        file.file, 
        s3_key, 
        file.content_type,
        metadata={
            "document_id": str(document_id),
            "uploaded_by": str(current_user.id),
            "source_type": source_type
        }
    )
    
    if not upload_success:
        raise HTTPException(
            status_code=500, 
            detail="Failed to upload document to storage"
        )
    
    # Save document to database
    session.add(document)
    session.commit()
    session.refresh(document)
    
    # Start background processing
    background_tasks.add_task(
        process_document_async,
        document_id=document_id,
        session=session
    )
    
    return document


@router.delete("/{document_id}")
async def delete_document(
    current_user: Annotated[User, Depends(require_document_delete_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """Delete a document and its chunks"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from S3 first
    s3_delete_success = s3_service.delete_file(document.file_path)
    if not s3_delete_success:
        # Continue with database deletion but log the issue
        # In production, consider how to handle this case (retry, alert, etc.)
        pass
    
    # Delete associated chunks
    chunks_query = select(DocumentChunk).where(DocumentChunk.document_id == str(document_id))
    chunks = session.exec(chunks_query).all()
    for chunk in chunks:
        session.delete(chunk)
    
    # Delete the document
    session.delete(document)
    session.commit()
    
    return JSONResponse(content={"message": "Document and associated chunks deleted successfully"})


@router.get("/{document_id}/chunks", response_model=List[DocumentChunk])
async def get_document_chunks(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    chunk_type: Optional[str] = Query(None, description="Filter by chunk type (text, table)"),
) -> Any:
    """Get chunks for a specific document with optional filtering by type"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Base query
    query = select(DocumentChunk).where(DocumentChunk.document_id == str(document_id))
    
    # Apply chunk type filter if provided
    if chunk_type:
        query = query.where(DocumentChunk.metadata_json.contains(f'"type": "{chunk_type}"'))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    chunks = session.exec(query).all()
    return chunks


@router.get("/{document_id}/download-url")
async def get_document_download_url(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
    expiration: int = Query(3600, description="URL expiration time in seconds"),
) -> Any:
    """Generate a pre-signed URL for downloading the document"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Generate presigned URL
    url = s3_service.get_file_url(document.file_path, expiration=expiration)
    
    if not url:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate download URL"
        )
    
    return JSONResponse(content={"download_url": url, "expires_in": expiration})


@router.patch("/{document_id}", response_model=Document)
async def update_document(
    current_user: Annotated[User, Depends(require_document_upload_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
    title: Optional[str] = Form(None),
    source_type: Optional[DocumentSourceType] = Form(None),
    source_name: Optional[str] = Form(None),
) -> Any:
    """Update document metadata"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Only allow updating metadata fields
    update_data: Dict[str, Any] = {}
    
    if title is not None:
        update_data["title"] = title
        
    if source_type is not None:
        update_data["source_type"] = source_type
        
    if source_name is not None:
        update_data["source_name"] = source_name
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Update the document
        for key, value in update_data.items():
            setattr(document, key, value)
        
        session.add(document)
        session.commit()
        session.refresh(document)
    
    return document 