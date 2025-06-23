from typing import Any, List, Optional, Dict, Annotated
import uuid
import os
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel import select, desc, update
import logging
import hashlib

from app.api.deps import CurrentUser, SessionDep, get_user_with_permission
from app.core.models.document import Document, DocumentChunk, DocumentResponse
from app.core.config.constants import DocumentSourceType, DocumentStatus, ChunkingStrategy, StageStatus
from app.core.config.settings import settings
from app.core.models.user import User
from app.core.services.s3 import s3_service
from app.core.services.document_processor import document_processor
from app.core.services.pipeline_processor import pipeline_processor
from app.core.config.processing_config import ParseConfig, ParserType
from app.core.services.config_service import config_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Permission-based dependencies
def require_document_upload_permission(current_user: CurrentUser) -> User:
    return get_user_with_permission("documents:create")(current_user)

def require_document_delete_permission(current_user: CurrentUser) -> User:
    return get_user_with_permission("documents:delete")(current_user)

def require_document_read_permission(current_user: CurrentUser) -> User:
    return get_user_with_permission("documents:read")(current_user)


@router.get("/", response_model=List[DocumentResponse])
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
    return [DocumentResponse.from_document(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """Get a specific document by ID"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.from_document(document)


@router.post("/", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_document_upload_permission)],
    session: SessionDep,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    source_type: DocumentSourceType = Form(DocumentSourceType.PDF),
    source_name: Optional[str] = Form(None),
    run_pipeline: bool = Form(True),
) -> Any:
    """Upload a document and optionally start processing pipeline"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file.content_type}. Only PDF files are supported."
        )
    
    # Generate document ID and file path
    document_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    s3_filename = f"{document_id}{file_extension}"
    s3_key = f"documents/{s3_filename}"
    
    # Read file content for hash calculation
    file_content = await file.read()
    file.file.seek(0)  # Reset file pointer
    
    # Calculate binary hash for deduplication
    binary_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check for existing document with same hash (deduplication)
    existing_doc = session.exec(
        select(Document).where(Document.binary_hash == binary_hash)
    ).first()
    
    if existing_doc:
        logger.info(f"Document with hash {binary_hash} already exists: {existing_doc.id}")
        # Return existing document instead of creating duplicate
        return DocumentResponse.from_document(existing_doc)
    
    # Create document record
    document = Document(
        id=str(document_id),
        filename=file.filename,
        title=title or os.path.splitext(file.filename)[0],
        source_type=source_type,
        source_name=source_name,
        file_path=s3_key,
        content_type=file.content_type,
        file_size=len(file_content),
        binary_hash=binary_hash,
    )
    
    from datetime import datetime, timezone
    
    # Set initial parse status based on whether we're starting the pipeline immediately
    parse_status = "running" if run_pipeline else "waiting"
    parse_stage_data = {
        "status": parse_status,
        "config": {
            "do_ocr": True,
            "do_table_structure": True,
            "ocr_language": "en"
        }
    }
    if run_pipeline:
        parse_stage_data["started_at"] = datetime.now(timezone.utc).isoformat()
    
    # Use simplified status structure with only stages (no legacy current_stage/stage_status fields)
    document.status_dict = {
        "stages": {
            "upload": {
                "status": "completed",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "attempts": 1
            },
            "parse": parse_stage_data,
            "chunk": {
                "status": "waiting", 
                "config": {
                    "strategy": "recursive",
                    "chunk_size": 1000,
                    "chunk_overlap": 200
                }
            },
            "index": {
                "status": "waiting",
                "config": {
                    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                    "index_type": "faiss"
                }
            }
        }
    }
    
    # Set clean metadata with only static document characteristics
    document.metadata_dict = {
        "uploaded_by": str(current_user.id),
        "original_filename": file.filename,
        # Additional document characteristics will be added after parsing
        # such as: page_count, is_scanned, table_count, etc.
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
            "source_type": source_type,
            "binary_hash": binary_hash
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
    
    # Start pipeline processing if requested
    if run_pipeline:
        background_tasks.add_task(
            process_stage_async,
            str(document_id),
            "parse"
        )
    
    return DocumentResponse.from_document(document)


@router.delete("/{document_id}")
async def delete_document(
    current_user: Annotated[User, Depends(require_document_delete_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """Delete a document, its chunks, and all associated files from S3"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    logger.info(f"Deleting document {document_id} ({document.filename})")
    
    # Track deletion results
    deletion_results = {
        "original_file": False,
        "parsed_results": [],
        "table_files": [],
        "chunks_deleted": 0
    }
    
    # 1. Delete original document from S3
    original_delete_success = s3_service.delete_file(document.file_path)
    deletion_results["original_file"] = original_delete_success
    
    if not original_delete_success:
        logger.warning(f"Failed to delete original file: {document.file_path}")
    
    # 2. Delete parsing results and table files from S3
    status_dict = document.status_dict
    stages = status_dict.get("stages", {})
    parse_stage = stages.get("parse", {})
    parse_result = parse_stage.get("result", {})
    
    # Delete main parsing result file
    result_key = parse_result.get("result_key")
    if result_key:
        try:
            # Extract S3 key from result_key (remove 'results/' prefix if present)
            s3_key = result_key
            if s3_key.startswith("results/"):
                s3_key = s3_key[8:]  # Remove 'results/' prefix
            
            delete_success = s3_service.delete_file(f"results/{s3_key}")
            deletion_results["parsed_results"].append({
                "key": result_key,
                "success": delete_success
            })
            
            if delete_success:
                logger.info(f"Deleted parsing result: {result_key}")
            else:
                logger.warning(f"Failed to delete parsing result: {result_key}")
                
        except Exception as e:
            logger.error(f"Error deleting parsing result {result_key}: {e}")
            deletion_results["parsed_results"].append({
                "key": result_key,
                "success": False,
                "error": str(e)
            })
    
    # Delete table files
    table_keys = parse_result.get("table_keys", [])
    for table_key in table_keys:
        try:
            # Extract S3 key from table_key (remove 'results/' prefix if present)
            s3_key = table_key
            if s3_key.startswith("results/"):
                s3_key = s3_key[8:]  # Remove 'results/' prefix
            
            delete_success = s3_service.delete_file(f"results/{s3_key}")
            deletion_results["table_files"].append({
                "key": table_key,
                "success": delete_success
            })
            
            if delete_success:
                logger.info(f"Deleted table file: {table_key}")
            else:
                logger.warning(f"Failed to delete table file: {table_key}")
                
        except Exception as e:
            logger.error(f"Error deleting table file {table_key}: {e}")
            deletion_results["table_files"].append({
                "key": table_key,
                "success": False,
                "error": str(e)
            })
    
    # 3. Delete associated chunks from database
    chunks_query = select(DocumentChunk).where(DocumentChunk.document_id == str(document_id))
    chunks = session.exec(chunks_query).all()
    for chunk in chunks:
        session.delete(chunk)
    deletion_results["chunks_deleted"] = len(chunks)
    
    # 4. Delete the document from database
    session.delete(document)
    session.commit()
    
    # 5. Prepare response message
    total_parsed_files = len(deletion_results["parsed_results"]) + len(deletion_results["table_files"])
    successful_parsed_deletions = (
        sum(1 for r in deletion_results["parsed_results"] if r["success"]) +
        sum(1 for r in deletion_results["table_files"] if r["success"])
    )
    
    message = f"Document '{document.filename}' deleted successfully"
    details = [
        f"Database record: deleted",
        f"Original file: {'deleted' if deletion_results['original_file'] else 'failed to delete'}",
        f"Chunks: {deletion_results['chunks_deleted']} deleted",
        f"Parsing results: {successful_parsed_deletions}/{total_parsed_files} deleted"
    ]
    
    logger.info(f"Document deletion completed: {message}")
    logger.info(f"Deletion details: {', '.join(details)}")
    
    return JSONResponse(content={
        "message": message,
        "details": details,
        "deletion_results": deletion_results
    })


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


@router.post("/{document_id}/stages/{stage}/start")
async def start_document_stage(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_document_upload_permission)],
    document_id: uuid.UUID,
    stage: str,
    session: SessionDep,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Any:
    """Start or retry a specific processing stage"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Validate stage
    if stage not in ["parse", "chunk-index"]:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}. Must be 'parse' or 'chunk-index'")
    
    # Get stages from the new status structure
    status_dict = document.status_dict
    stages = status_dict.get("stages", {})
    current_stage_status = stages.get(stage, {}).get("status")
    
    # Check if stage can be started
    if current_stage_status == "running":
        raise HTTPException(status_code=400, detail=f"Stage '{stage}' is already running")
    
    # Check prerequisites
    if stage == "chunk-index":
        parse_status = stages.get("parse", {}).get("status")
        if parse_status != "completed":
            raise HTTPException(status_code=400, detail="Cannot start chunk-index: parsing must be completed first")
    
    # Update stage status to running
    from datetime import datetime, timezone
    stages[stage] = {
        **stages.get(stage, {}),
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "attempts": stages.get(stage, {}).get("attempts", 0) + 1,
        "error_message": None
    }
    
    # Add config overrides if provided
    if config_overrides:
        stages[stage]["config_overrides"] = config_overrides
    
    # Update the status structure (simplified - no redundant fields)
    status_dict["stages"] = stages
    document.status_dict = status_dict
    document.updated_at = datetime.now(timezone.utc)
    session.add(document)
    session.commit()
    
    # Start the stage processing in background
    background_tasks.add_task(
        process_stage_async,
        document_id=str(document_id),
        stage=stage
    )
    
    return {"message": f"Stage '{stage}' started successfully", "stages": document.status_dict.get("stages", {})}


@router.get("/{document_id}/stages/{stage}/error")
async def get_stage_error(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    stage: str,
    session: SessionDep,
) -> Any:
    """Get error details for a failed stage"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if stage not in ["upload", "parse", "chunk-index"]:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")
    
    stages = document.status_dict.get("stages", {})
    stage_info = stages.get(stage, {})
    
    if stage_info.get("status") != "failed":
        raise HTTPException(status_code=400, detail=f"Stage '{stage}' has not failed")
    
    return {
        "document_id": str(document_id),
        "stage": stage,
        "error_message": stage_info.get("error_message"),
        "failed_at": stage_info.get("failed_at"),
        "attempts": stage_info.get("attempts", 0),
        "config": stage_info.get("config_overrides", {})
    }


# Removed get_stage_progress endpoint - redundant with update_document_status


async def process_stage_async(document_id: str, stage: str) -> None:
    """Process a specific stage asynchronously"""
    from app.core.db import engine
    from sqlmodel import Session
    from datetime import datetime, timezone
    
    try:
        with Session(engine) as session:
            document = session.get(Document, document_id)
            if not document:
                return
            
            logger.info(f"Starting {stage} processing for document {document_id}")
            
            if stage == "parse":
                # Process parsing stage using RAGParser microservice
                logger.info(f"Starting parse stage for document {document_id}")
                
                # Import services
                from app.core.services.ragparser_client import ragparser_client
                from app.core.services.s3 import s3_service
                
                try:
                    # Generate presigned URL for RAGParser to access the document
                    document_url = s3_service.get_file_url(document.file_path, expiration=3600)
                    if not document_url:
                        raise Exception("Failed to generate document URL for RAGParser")
                    
                    # Get parsing config from stage
                    stages = document.status_dict
                    parse_config = stages["stages"].get("parse", {}).get("config", {})
                    
                    # Submit document to RAGParser
                    ragparser_response = await ragparser_client.submit_document_for_parsing(
                        document_url=document_url,
                        options={
                            "document_id": document_id,
                            "filename": document.filename,
                            "content_type": document.content_type,
                            **parse_config  # Include OCR and table extraction settings
                        }
                    )
                    
                    # Update document with task ID
                    document.ragparser_task_id = ragparser_response.task_id
                    
                    # Update stage status to running
                    stages["stages"]["parse"] = {
                        **stages["stages"].get("parse", {}),
                        "status": "running",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "ragparser_task_id": ragparser_response.task_id,
                        "queue_position": ragparser_response.queue_position
                    }
                    document.status_dict = stages
                    
                    # Commit changes
                    session.add(document)
                    session.commit()
                    
                    logger.info(f"Document {document_id} submitted to RAGParser with task_id: {ragparser_response.task_id}")
                    logger.info(f"Document task ID stored in database: {document.ragparser_task_id}")
                    
                    # Backend monitoring removed - using frontend polling only
                    
                except Exception as parse_error:
                    logger.error(f"Failed to submit document for parsing {document_id}: {parse_error}")
                    
                    # Update stage status to failed
                    stages = document.status_dict
                    stages["stages"]["parse"] = {
                        **stages["stages"].get("parse", {}),
                        "status": "failed",
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                        "error_message": str(parse_error),
                        "attempts": stages["stages"].get("parse", {}).get("attempts", 0) + 1
                    }
                    document.status_dict = stages
                    
                    session.add(document)
                    session.commit()
                    raise parse_error
                
            elif stage == "chunk-index":
                # Process combined chunking and indexing stage
                logger.info(f"Starting chunk-index stage for document {document_id}")
                
                # Import document processor
                from app.core.services.bulk_processor import BulkProcessor
                document_processor = BulkProcessor()
                
                # Process chunking - splits parsed text into chunks
                chunks = await document_processor.process_document(document, session)
                
                # TODO: Implement vector indexing logic here
                logger.info(f"Chunking completed for document {document_id}, indexing not yet implemented")
                
                # Update stage status using new status structure
                status_dict = document.status_dict
                stages = status_dict.get("stages", {})
                stages["chunk-index"] = {
                    **stages.get("chunk-index", {}),
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "chunks_created": len(chunks)
                }
                status_dict["stages"] = stages
                document.status_dict = status_dict
            
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            logger.info(f"Completed {stage} processing for document {document_id}")
            
    except Exception as e:
        logger.error(f"Error processing {stage} for document {document_id}: {e}")
        
        # Update stage status to failed
        try:
            with Session(engine) as session:
                document = session.get(Document, document_id)
                if document:
                    status_dict = document.status_dict
                    stages = status_dict.get("stages", {})
                    stages[stage] = {
                        **stages.get(stage, {}),
                        "status": "failed",
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                        "error_message": str(e)
                    }
                    status_dict["stages"] = stages
                    document.status_dict = status_dict
        except Exception as update_error:
            logger.error(f"Failed to update stage status after error: {update_error}")


def _extract_document_characteristics(ragparser_status: Dict[str, Any]) -> Dict[str, Any]:
    """Extract document structure characteristics from RAGParser status response"""
    characteristics = {}
    logger.info(f"_extract_document_characteristicsRAGParser status: {str(ragparser_status)}")
    
    if not isinstance(ragparser_status, dict):
        return characteristics

    try:
        # Extract from top-level fields
        if "pages_processed" in ragparser_status:
            characteristics["page_count"] = ragparser_status["pages_processed"]
        
        # Extract from document_info section
        document_info = ragparser_status.get("document_info")
        if document_info:
            # Check if document_info is already a parsed object or still a dict
            if hasattr(document_info, '__dict__'):
                # It's a parsed DocumentInfo object, access attributes directly
                if hasattr(document_info, 'table_count'):
                    characteristics["table_count"] = document_info.table_count
                if hasattr(document_info, 'image_count'):
                    characteristics["image_count"] = document_info.image_count
                if hasattr(document_info, 'text_length'):
                    characteristics["text_length"] = document_info.text_length
                if hasattr(document_info, 'word_count'):
                    characteristics["word_count"] = document_info.word_count
                if hasattr(document_info, 'is_scanned'):
                    characteristics["is_scanned"] = document_info.is_scanned
                if hasattr(document_info, 'language'):
                    characteristics["language"] = document_info.language
                if hasattr(document_info, 'rotated_pages'):
                    characteristics["rotated_pages"] = document_info.rotated_pages
                if hasattr(document_info, 'mime_type'):
                    characteristics["mime_type"] = document_info.mime_type
                if hasattr(document_info, 'pages_processed') and document_info.pages_processed is not None:
                    characteristics["page_count"] = document_info.pages_processed  # Override with more specific count if available
            else:
                # It's still a dictionary, use the original approach
                for key in ["mime_type", "table_count", "image_count", "text_length", "word_count", "is_scanned", "language", "rotated_pages"]:
                    if key in document_info:
                        characteristics[key] = document_info[key]
        
       
        
        logger.info(f"Extracted document characteristics: {characteristics}")
        
    except Exception as e:
        logger.warning(f"Error extracting document characteristics: {e}")
    
    return characteristics


async def _get_fallback_document_characteristics(document: Document, table_keys: Optional[List[str]]) -> Dict[str, Any]:
    """Get minimal document characteristics when RAGParser data is not available - no fake data"""
    try:
        # Base characteristics we know for certain
        characteristics = {
            "mime_type": document.content_type,
            "parsing_incomplete": True,
            "analysis_source": "fallback",
            "analysis_limitations": {
                "page_count": "unknown - parsing incomplete",
                "text_analysis": "unavailable - parsing incomplete", 
                "image_analysis": "unavailable - parsing incomplete",
                "language_detection": "unavailable - parsing incomplete"
            }
        }
        
        # Only include table info if we have actual table_keys from parsing
        if table_keys:
            characteristics.update({
                "table_count": len(table_keys),
                "has_tables": True
            })
        
        logger.warning(f"Using fallback characteristics for document {document.id} - RAGParser analysis incomplete")
        logger.info(f"Fallback characteristics: {characteristics}")
        
        return characteristics
        
    except Exception as e:
        logger.error(f"Failed to generate fallback characteristics: {e}")
        # Return minimal info on error
        return {
            "mime_type": document.content_type,
            "parsing_failed": True,
            "analysis_source": "error"
        }


async def process_parsed_results(
    document_id: str, 
    result_key: str, 
    table_keys: Optional[List[str]] = None, 
    ragparser_status: Optional[Dict[str, Any]] = None
    ) -> None:
    """Process the parsed results from RAGParser and extract document characteristics"""
    from app.core.db import engine
    from sqlmodel import Session
    from app.core.services.ragparser_client import ragparser_client
    from datetime import datetime, timezone
    
    # Always mark parsing as completed, even if result download fails
    parsing_completed = True
    
    try:
        with Session(engine) as session:
            document = session.get(Document, document_id)
            if not document:
                logger.error(f"Document {document_id} not found during result processing")
                return
            
            logger.info(f"Processing parsed results for document {document_id}")
            logger.info(f"Result key: {result_key}")
            logger.info(f"Table keys: {table_keys}")
            
            # Extract document characteristics from RAGParser status for metadata
            document_characteristics = {}
            
            if ragparser_status and ragparser_status.get("document_info"):
                logger.info(f"Extracting characteristics from RAGParser status for document {document_id}")
                document_characteristics = _extract_document_characteristics(ragparser_status)
            else:
                logger.warning(f"No RAGParser status data available for document {document_id} - using fallback")
                document_characteristics = await _get_fallback_document_characteristics(document, table_keys)
            
            # Update metadata with document characteristics only (no processing info)
            metadata = document.metadata_dict or {}
            if document_characteristics:
                metadata.setdefault("structure", {}).update(document_characteristics)
                logger.info(f"Updated document {document_id} metadata with structure: {document_characteristics}")
            
            document.metadata_dict = metadata
            
            # Update status with file references and extract completion data from RAGParser
            stages = document.status_dict
            stages.setdefault("stages", {})
            parse_stage = stages["stages"].setdefault("parse", {})
            
            # Extract and update parse stage data from RAGParser response in one operation
            if ragparser_status:
                parse_stage.update({
                    "status": "completed",  # We're processing results, so parsing is completed
                    "completed_at": ragparser_status.get("completed_at", datetime.now(timezone.utc).isoformat()),
                    "parser_used": ragparser_status.get("parser_used", parse_stage.get("parser_used")),
                    "pages_processed": ragparser_status.get("pages_processed", parse_stage.get("pages_processed"))
                })
            else:
                # Fallback update if no RAGParser status provided
                parse_stage.update({
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                })
            
            # Update result data in one operation
            parse_stage.setdefault("result", {}).update({
                "result_key": result_key,
                "table_keys": table_keys or []
            })
            
            document.status_dict = stages
            
            session.add(document)
            session.commit()
            
            logger.info(f"Successfully processed document characteristics for document {document_id}")
            
    except Exception as e:
        logger.error(f"Error processing document characteristics for document {document_id}: {e}")
        
        # Don't fail the parsing stage - just log the error
        # The document parsing is still considered successful even if metadata extraction fails
        try:
            with Session(engine) as session:
                document = session.get(Document, document_id)
                if document:
                    logger.warning(f"Metadata extraction failed for document {document_id}, but parsing remains completed")
                    # Just save the document without failing the parse stage
                    session.add(document)
                    session.commit()
        except Exception as update_error:
            logger.error(f"Failed to save document after metadata extraction error: {update_error}")


@router.post("/{document_id}/reparse")
async def reparse_document(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_document_upload_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
    parse_config: ParseConfig,
) -> Dict[str, str]:
    """
    Reparse a document with new parser configuration
    This will reset the document to parse stage and use the new parser settings
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if parsing is currently running and cancel if needed
    status_dict = document.status_dict
    current_parse_status = status_dict.get("stages", {}).get("parse", {}).get("status")
    
    if current_parse_status == "running":
        logger.warning(f"Cancelling existing parse task for document {document_id}")
        # TODO: Implement RAGParser task cancellation
        # if document.ragparser_task_id:
        #     await ragparser_client.cancel_task(document.ragparser_task_id)
    
    try:
        # Update document's parse configuration
        document.parse_config = parse_config
        
        # Reset document status using the new structure
        status_data = document.status_dict
        
        # Update parse stage with new config
        status_data["stages"]["parse"] = {
            "status": "waiting",
            "config": parse_config.dict(),  # Store the new config in the stage
            "attempts": 0
        }
        
        # Reset downstream stages
        status_data["stages"]["chunk"] = {"status": "waiting"}
        status_data["stages"]["index"] = {"status": "waiting"}
        
        document.status_dict = status_data
        document.updated_at = datetime.now(timezone.utc)
        
        # Note: Don't clear ragparser_task_id here - let process_stage_async set the new one
        # to avoid race conditions
        
        session.add(document)
        session.commit()
        
        # Use the NEW pathway that properly handles status structure and config
        background_tasks.add_task(process_stage_async, str(document_id), "parse")
        
        return {
            "message": f"Document reparse started with {parse_config.parser_type} parser",
            "document_id": str(document_id),
            "parser_type": parse_config.parser_type
        }
        
    except Exception as e:
        logger.error(f"Error starting document reparse: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start reparse: {str(e)}")


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_document_upload_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, str]:
    """
    Reprocess a document with current global chunk and index configuration
    This will reset chunk and index stages and reprocess with current global settings
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Check if parse stage is completed
        status_data = document.status_dict
        parse_status = status_data.get("stages", {}).get("parse", {}).get("status")
        
        if parse_status != "completed":
            raise HTTPException(
                status_code=400, 
                detail="Cannot reprocess document - parse stage must be completed first"
            )
        
        # Reset chunk and index stages
        status_data["stages"]["chunk"] = {
            "status": "waiting",
            "metrics": {}
        }
        status_data["stages"]["index"] = {
            "status": "waiting",
            "metrics": {}
        }
        
        # Remove legacy fields - only use stages structure
        # status_data["current_stage"] = "chunk"
        # status_data["stage_status"] = "waiting"
        
        document.status_dict = status_data
        document.updated_at = datetime.now(timezone.utc)
        
        session.add(document)
        session.commit()
        
        # Start reprocessing from chunk stage
        background_tasks.add_task(start_chunk_processing_async, str(document_id))
        
        return {
            "message": "Document reprocessing started with current global configuration",
            "document_id": str(document_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting document reprocessing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start reprocessing: {str(e)}")


@router.get("/{document_id}/parse-config", response_model=Dict[str, Any])
async def get_document_parse_config(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, Any]:
    """Get the current parse configuration for a document"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "document_id": str(document_id),
        "parse_config": document.parse_config.dict(),
        "available_parsers": [parser.value for parser in ParserType]
    }


@router.get("/{document_id}/quality-metrics", response_model=Dict[str, Any])
async def get_document_quality_metrics(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, Any]:
    """Get quality metrics for all stages of a document"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    stages = document.stages
    metrics = {}
    
    for stage_name, stage_data in stages.items():
        if "metrics" in stage_data:
            metrics[stage_name] = stage_data["metrics"]
    
    return {
        "document_id": str(document_id),
        "metrics": metrics,
        "overall_status": document.overall_status
    }


@router.get("/{document_id}/parse-results", response_model=Dict[str, Any])
async def get_parse_results(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, Any]:
    """Get parse results from RAGParser response data"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get parse stage info
    status_dict = document.status_dict
    parse_stage = status_dict.get("stages", {}).get("parse", {})
    
    if parse_stage.get("status") != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Parse stage not completed. Current status: {parse_stage.get('status', 'unknown')}"
        )
    
    # Get RAGParser result from parse stage
    parse_result = parse_stage.get("result", {})
    if not parse_result:
        raise HTTPException(status_code=404, detail="Parse results not found")
    
    # Determine parser type from config or result
    parser_type = parse_stage.get("config", {}).get("parser_type", "unknown")
    
    return {
        "document_id": str(document_id),
        "parse_result": parse_result,
        "status": parse_stage.get("status"),
        "completed_at": parse_stage.get("completed_at"),
        "parser_type": parser_type
    }


@router.post("/{document_id}/update-status", response_model=DocumentResponse)
async def update_document_status(
    current_user: Annotated[User, Depends(require_document_read_permission)],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """Refresh document status from backend and check RAGParser if task is running"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # If there's a RAGParser task running, check its status
    if document.ragparser_task_id:
        stages = document.status_dict
        parse_stage = stages.get("stages", {}).get("parse", {})
        
        try:
            logger.info(f"Manually checking RAGParser status for task {document.ragparser_task_id}")
            
            from app.core.services.ragparser_client import ragparser_client
            status = await ragparser_client.get_task_status_new(document.ragparser_task_id)
            
            if hasattr(status, 'model_dump'):
                import json
                logger.info(f"RAGParser status details: {json.dumps(status.model_dump, indent=2, default=str)}")
            
            # Update progress
            stages["stages"]["parse"] = {
                **parse_stage,
                "progress": status.progress,
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
            if status.state == "completed":
                logger.info(f"Document {document_id} parsing completed - updating status")
                stages["stages"]["parse"] = {
                    **parse_stage,
                    "started_at": getattr(status, 'started_at', settings.UNKNOWN_VALUE),
                    "completed_at": getattr(status, 'completed_at', settings.UNKNOWN_VALUE),
                    "progress": getattr(status, 'progress', settings.UNKNOWN_VALUE),
                    "parser_used": getattr(status, 'parser_used', settings.UNKNOWN_VALUE),
                    "ragparser_task_id": getattr(status, 'ragparser_task_id', settings.UNKNOWN_VALUE),
                    "attempts": parse_stage.get("attempts", 1),
                    "result": {
                        "result_key": status.result_key,
                        "table_keys": status.table_keys or []
                    },
                    "config": parse_stage.get("config", {}),
                    "pages_processed": getattr(status, 'pages_processed', settings.UNKNOWN_VALUE),
                    "document_info": getattr(status, 'document_info', {})
                }
                
                # Process parsed results now that parsing is complete - call synchronously to ensure status is updated properly
                try:
                    # Extract document characteristics from status
                    ragparser_status_data = stages["stages"]["parse"] 
                    # Call process_parsed_results to extract and store document characteristics
                    # Note: process_parsed_results will set status to "completed" and completed_at timestamp
                    await process_parsed_results(
                        str(document_id), 
                        status.result_key, 
                        status.table_keys, 
                        ragparser_status_data
                    )
                    logger.info(f"Completed result processing for document {document_id}")
                    # Refresh document from database since process_parsed_results committed changes
                    session.refresh(document)
                    return DocumentResponse.from_document(document)
                except Exception as process_error:
                    logger.error(f"Failed to process results for document {document_id}: {process_error}")
                    # If result processing fails, still mark parse as completed
                    stages["stages"]["parse"]["status"] = "completed"
                    stages["stages"]["parse"]["completed_at"] = datetime.now(timezone.utc).isoformat()
                    document.status_dict = stages
                
            elif status.state == "failed":
                logger.error(f"Document {document_id} parsing failed: {status.error}")
                stages["stages"]["parse"] = {
                    **parse_stage,
                    "status": "failed",
                    "failed_at": status.failed_at,
                    "error_message": status.error
                }
            
            document.status_dict = stages
            
        except Exception as e:
            logger.error(f"Failed to check RAGParser status during manual update: {e}")
            # Don't fail the whole request, just log the error
    
    # Update the document's updated_at timestamp
    document.updated_at = datetime.now(timezone.utc)
    session.add(document)
    session.commit()
    session.refresh(document)
    
    logger.info(f"Updated document status for document {document_id}")
    
    return DocumentResponse.from_document(document)


async def start_chunk_processing_async(document_id: str) -> None:
    """
    Background task to start chunk and index processing for a document
    """
    from app.core.db import engine
    from sqlmodel import Session
    
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if not document:
            logger.error(f"Document {document_id} not found for chunk processing")
            return
        
        try:
            # Start chunk processing
            await pipeline_processor.process_chunk_stage(document, session)
            
            # If chunk stage succeeds, start index processing
            if document.stages.get("chunk", {}).get("status") == "completed":
                await pipeline_processor.process_index_stage(document, session)
                
        except Exception as e:
            logger.error(f"Chunk/Index processing failed for document {document_id}: {e}")
            # Update document status to failed
            document.update_stage_status("chunk", "failed", error_message=str(e))
            session.add(document)
            session.commit()