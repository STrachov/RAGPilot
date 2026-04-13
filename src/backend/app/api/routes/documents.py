from typing import Any, List, Optional, Dict, Annotated
import uuid
import os
import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel import select, desc, update, func, delete, Session
import logging
import hashlib
from io import BytesIO

from app.api.deps import CurrentUser, SessionDep, get_user_with_permission
from app.core.models.document import Document, DocumentChunk, DocumentResponse
from app.core.config.constants import DocumentSourceType, DocumentStatus
from app.core.config.settings import settings
from app.core.models.user import User
from app.core.services.s3 import s3_service
from app.core.services.dynamic_pipeline import dynamic_pipeline_service
from app.core.config.constants import ParseConfig, ParserType, ChunkConfig, IndexConfig, UploadConfig
from app.core.services.config_service import config_service
from app.core.services.ragparser_client import ragparser_client
from app.core.exceptions import TaskNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()

# Permission-based dependencies - REMOVED (these were broken)
# def require_document_upload_permission(current_user: CurrentUser) -> User:
#     return get_user_with_permission("documents:create")(current_user)

# def require_document_delete_permission(current_user: CurrentUser) -> User:
#     return get_user_with_permission("documents:delete")(current_user)

# def require_document_read_permission(current_user: CurrentUser) -> User:
#     return get_user_with_permission("documents:read")(current_user)

# def require_document_admin_permission(current_user: CurrentUser) -> User:
#     return get_user_with_permission("documents:admin")(current_user)


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    session: SessionDep,
    skip: int = 0, 
    limit: int = 100,
    status: Optional[DocumentStatus] = None,
    source_type: Optional[DocumentSourceType] = None,
) -> Any:
    """List all documents with optional filtering"""
    try:
        query = select(Document).offset(skip).limit(limit).order_by(desc(Document.created_at))
        
        if status:
            query = query.where(Document.status == status)
        
        if source_type:
            query = query.where(Document.source_type == source_type)
            
        documents = session.exec(query).all()
        return [DocumentResponse.from_document(doc) for doc in documents]
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@router.get("/pipelines", response_model=Dict[str, Any])
async def get_available_pipelines(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
) -> Any:
    """
    Get a list of available processing pipelines with their definitions.
    
    This endpoint provides clients with the available pipeline templates
    that can be used to process documents.
    """
    try:
        pipelines = dynamic_pipeline_service.get_predefined_pipelines()
        return {name: pipeline.model_dump() for name, pipeline in pipelines.items()}
    except Exception as e:
        logger.error(f"Failed to get available pipelines: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve available pipelines: {str(e)}"
        )


@router.get("/stages", response_model=Dict[str, Any])
async def get_available_stages(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))]
) -> Any:
    """
    Get a list of available pipeline stages with their metadata.
    
    This endpoint provides clients with the available stages that can be
    used to construct custom pipelines.
    """
    try:
        logger.info(f"Getting available stages for user {current_user.id}")
        stages = dynamic_pipeline_service.get_available_stages()
        return {stage.name: stage.model_dump() for stage in stages}
    except Exception as e:
        logger.error(f"Failed to get available stages: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve available stages: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """Get a specific document by ID"""
    try:
        document = session.get(Document, str(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentResponse.from_document(document)
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}"
        )


@router.post("/", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_user_with_permission("documents:create"))],
    session: SessionDep,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    source_type: DocumentSourceType = Form(DocumentSourceType.PDF),
    source_name: Optional[str] = Form(None),
    run_pipeline: bool = Form(True),
) -> Any:
    """Upload a document and optionally start the default processing pipeline"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if file.content_type not in UploadConfig().allowed_document_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file.content_type}. Only {UploadConfig().allowed_document_types.keys()} files are supported."
        )
    start_time = datetime.now(timezone.utc).isoformat()
    # Generate document ID and file path
    document_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    s3_filename = f"{document_id}{file_extension}"
    s3_key = f"documents/{s3_filename}"
    
    # Read file content for hash calculation
    file_content = await file.read()
    await file.seek(0)  # Reset file pointer
    
    # Calculate binary hash for deduplication
    binary_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check for existing document with same hash (deduplication)
    existing_doc = session.exec(
        select(Document).where(Document.binary_hash == binary_hash)
    ).first()
    
    if existing_doc:
        logger.info(f"Document with hash {binary_hash} already exists: {existing_doc.id}")
        return DocumentResponse.from_document(existing_doc)
    
    # Create document record
    document = Document(
        id=str(document_id),
        filename=file.filename,
        title=title or os.path.splitext(file.filename)[0],
        source_type=source_type,
        source_name=source_name,
        content_type=file.content_type,
        file_size=len(file_content),
        binary_hash=binary_hash,
    )
    # Initialize status with waiting stages
    document.status_dict = document.get_default_status_structure()
    logger.info(f"Default document status dict: {document.status_dict}")
    # Set clean metadata
    document.metadata_dict = {
        "uploaded_by": str(current_user.id),
        "original_filename": file.filename,
    }
    
    session.add(document)
    
    # Upload file to S3
    try:
        file_obj = BytesIO(file_content)
        s3_service.upload_file(
            file_obj, 
            s3_key, 
            file.content_type,
            metadata={ "document_id": str(document_id) }
        )
        document.file_path = s3_key
        logger.info(f"Upload params: {s3_key}, {file.content_type}")
        # Mark upload stage as completed
        status = document.status_dict
        status['stages']['upload'] = {
                    "status": "completed",
                    "started_at": start_time,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "result": {
                        "stage_type": "upload",
                        "file_path": s3_key,
                        "file_size": len(file_content),
                    }
        }
        document.status_dict = status
        logger.info(f"Document status dict after upload: {document.status_dict}")
        
    except Exception as e:
        logger.error(f"Failed to upload document {document.id} to S3: {e}")
        document.status_dict['stages']['upload'] = {
            "status": "failed",
            "error_message": str(e),
            "started_at": start_time.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Failed document status dict after upload: {document.status_dict}")
        session.commit()
        raise HTTPException(status_code=500, detail="Failed to upload file to storage.")

    session.commit()
    session.refresh(document)
    
    # If run_pipeline is true, start the default pipeline
    if run_pipeline:
         # Get the default pipeline name from global config
        global_config = config_service.get_global_config()
        pipeline_name = global_config.pipeline_name
        logger.info(f"Automatically starting pipeline '{pipeline_name}' for document {document.id}")
        background_tasks.add_task(
            dynamic_pipeline_service.execute_pipeline,
            pipeline_name=pipeline_name,
            document_id=str(document.id),
            session=session
        )
    
    return DocumentResponse.from_document(document)


@router.delete("/{document_id}")
async def delete_document(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:delete"))],
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
        "chunks": 0,
        "database_records": 0,
        "errors": []
    }
    
    # 1. Delete original file from S3
    if document.file_path:
        try:
            s3_service.delete_file(document.file_path)
            deletion_results["original_file"] = True
            logger.info(f"Deleted original file {document.file_path} from S3")
        except Exception as e:
            error_msg = f"Error deleting original file from S3: {e}"
            logger.error(error_msg)
            deletion_results["errors"].append(error_msg)
            
    # 2. Delete parsed results from S3 (if any)
    doc_stages = document.status_dict.get("stages", {})
    parse_result = doc_stages.get("parse", {}).get("result", {})
    if parse_result and "result_key" in parse_result:
        try:
            s3_service.delete_file(parse_result["result_key"])
            deletion_results["parsed_results"].append(parse_result["result_key"])
            logger.info(f"Deleted parsed result file {parse_result['result_key']} from S3")
        except Exception as e:
            error_msg = f"Error deleting parsed result file from S3: {e}"
            logger.error(error_msg)
            deletion_results["errors"].append(error_msg)
            
    # 3. Delete chunks from database
    chunk_delete_statement = delete(DocumentChunk).where(DocumentChunk.document_id == str(document_id))
    chunk_result = session.exec(chunk_delete_statement)
    session.commit()
    deletion_results["chunks"] = chunk_result.rowcount
    logger.info(f"Deleted {chunk_result.rowcount} chunks from database")
    
    # 4. Delete document record from database
    session.delete(document)
    session.commit()
    deletion_results["database_records"] = 1
    logger.info(f"Deleted document record {document_id} from database")
    
    return JSONResponse(
        status_code=200,
        content={
            "message": f"Deletion process for document {document_id} completed",
            "details": deletion_results
        }
    )

@router.get("/{document_id}/chunks", response_model=List[DocumentChunk])
async def get_document_chunks(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    chunk_type: Optional[str] = Query(None, description="Filter by chunk type (text, table)"),
) -> Any:
    """Get all chunks for a document"""
    query = select(DocumentChunk).where(DocumentChunk.document_id == str(document_id)).offset(skip).limit(limit)
    
    if chunk_type:
        # This requires a JSON-aware query, which can be database-specific
        # Using a simple string search for now, which may not be perfectly accurate
        query = query.filter(func.json_extract(DocumentChunk.metadata, "$.type") == chunk_type)
        
    chunks = session.exec(query).all()
    return chunks


@router.get("/{document_id}/download-url")
async def get_document_download_url(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    session: SessionDep,
    expiration: int = Query(3600, description="URL expiration time in seconds"),
) -> Any:
    """Get a presigned download URL for the document's original file"""
    document = session.get(Document, str(document_id))
    if not document or not document.file_path:
        raise HTTPException(status_code=404, detail="Document file not found")
        
    url = s3_service.get_file_url(document.file_path, expiration)
    if not url:
        raise HTTPException(status_code=500, detail="Could not generate download URL")
        
    return {"url": url}


@router.post("/{document_id}/stages/{stage}/start")
async def start_document_stage(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_user_with_permission("documents:create"))],
    document_id: uuid.UUID,
    stage: str,
    session: SessionDep,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Start a specific processing stage for a document.
    This is now a wrapper around the single-stage execution in dynamic_pipeline_service.
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    logger.info(f"Manually starting stage '{stage}' for document {document_id}")
    stage_config = config_overrides or config_service.get_stage_config(stage)
    logger.info(f"Stage config: {stage_config}")

    # Use a background task to run the single stage via the pipeline executor
    background_tasks.add_task(
        dynamic_pipeline_service.execute_single_stage,
        document_id=str(document_id),
        stage_name=stage,
        session=session,
        config=stage_config,
    )

    return {"message": f"Stage '{stage}' has been initiated for document {document_id}."}


@router.get("/{document_id}/stages/{stage}/status")
async def get_stage_status(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    stage: str,
    session: SessionDep,
) -> Any:
    """Get the status of a specific stage for a document"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc_stages = document.status_dict.get("stages", {})
    stage_status = doc_stages.get(stage)
    
    if not stage_status:
        raise HTTPException(status_code=404, detail=f"Stage '{stage}' not found for this document")
        
    return stage_status


@router.get("/{document_id}/stages/{stage}/error")
async def get_stage_error(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    stage: str,
    session: SessionDep,
) -> Any:
    """Get the error message if a stage has failed"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc_stages = document.status_dict.get("stages", {})
    stage_status = doc_stages.get(stage, {})
    
    if stage_status.get("status") != "failed":
        return {"error_message": None}
        
    return {"error_message": stage_status.get("error_message")}

@router.post("/{document_id}/pipelines/{pipeline_name}/execute")
async def execute_document_pipeline(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_user_with_permission("documents:create"))],
    document_id: uuid.UUID,
    pipeline_name: str,
    session: SessionDep,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Any:
    """Execute a predefined pipeline for a document"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Use a background task to run the pipeline
    background_tasks.add_task(
        dynamic_pipeline_service.execute_pipeline,
        pipeline_name=pipeline_name,
        document_id=str(document_id),
        session=session,
        config_overrides=config_overrides,
    )

    return {"message": f"Pipeline '{pipeline_name}' has been initiated for document {document_id}."}

@router.get("/{document_id}/pipelines/{pipeline_name}/status")
async def get_pipeline_execution_status(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    pipeline_name: str,
    session: SessionDep,
) -> Any:
    """
    Get the status of the latest execution for a given pipeline on a document.
    NOTE: This is a simplified implementation. A real-world scenario would require
    storing and querying pipeline execution history.
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # This simplified version just returns the current stage statuses from the document
    # which reflects the last-run pipeline.
    return {
        "document_id": document.id,
        "pipeline_name": pipeline_name,
        "status": "No direct execution tracking, showing current document stage statuses",
        "stage_statuses": document.status_dict.get("stages", {})
    }

# TODO: This is a temporary endpoint. It should be removed when the parse feature is implemented.
@router.post("/{document_id}/reparse")
async def parse_document(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_user_with_permission("documents:create"))],
    document_id: uuid.UUID,
    session: SessionDep,
    parse_config: ParseConfig,
) -> Dict[str, str]:
    """
    Reparse a document with a new parsing configuration.
    This will trigger the 'parse' stage again.
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Use a background task to re-run the parse stage
    background_tasks.add_task(
        dynamic_pipeline_service.execute_single_stage,
        document_id=str(document_id),
        stage_name="parse",
        session=session,
        config=parse_config.model_dump(),
    )

    return {"message": "Reparsing initiated. The document's parse stage is now running."}

# TODO: This is a temporary endpoint. It should be removed when the pipeline feature is implemented.
@router.post("/{document_id}/reprocess")
async def reprocess_document(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_user_with_permission("documents:create"))],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, str]:
    """
    Reprocess a document using the configured default pipeline.
    This will re-run chunking and indexing based on the latest parsed data.
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get the default pipeline name from global config
    global_config = config_service.get_global_config()
    pipeline_name = global_config.pipeline_name

    # Use a background task to run the default RAG pipeline
    background_tasks.add_task(
        dynamic_pipeline_service.execute_pipeline,
        pipeline_name=pipeline_name,
        document_id=str(document_id),
        session=session,
    )

    return {"message": f"Reprocessing initiated for document {document_id} using the '{global_config.pipeline_name}' pipeline."}


@router.get("/{document_id}/parse-config", response_model=Dict[str, Any])
async def get_document_parse_config(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, Any]:
    """Get the current parsing configuration for a document"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc_stages = document.status_dict.get("stages", {})
    parse_config = doc_stages.get("parse", {}).get("config", {})
    return parse_config


@router.get("/{document_id}/quality-metrics", response_model=Dict[str, Any])
async def get_document_quality_metrics(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, Any]:
    """Get quality metrics for a document from its metadata"""
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    metadata = document.metadata_dict
    quality_metrics = {
        k: v for k, v in metadata.items() 
        if k in ["readability_score", "text_to_noise_ratio", "ocr_confidence"]
    }
    return quality_metrics


@router.get("/{document_id}/parse-results", response_model=Dict[str, Any])
async def get_parse_results(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, Any]:
    """
    Get the parsed results for a document from S3.
    This downloads and returns the JSON output from RAGParser.
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    doc_metadata = document.metadata_dict
    doc_stages = document.status_dict.get("stages", {})
    parse_stage = doc_stages.get("parse", {})
    
    if parse_stage.get("status") != "completed":
        raise HTTPException(status_code=404, detail="Parsing is not yet completed for this document")
    
    parse_result = parse_stage.get("result", {})
    if not parse_result:
        raise HTTPException(status_code=404, detail="Parsed result file key not found")
    
    try:
    # Fields to return:
    # document_id: string;
    # parse_result: Record<string, any>;
    # status: string;
    # finished_at?: string;
    # parser_type: string;

    # Documents parse stage status:
    # "parse": {
    # "status": "completed", 
    # "started_at": "2025-07-24T14:08:02.360602+00:00Z", 
    # "finished_at": "2025-07-24T17:08:11.130099Z", 
    # "result": {"stage_type": "parse", "parser_name": "ragparser", "parser_version": "docling-2.33.0", "task_id": "ragpilot-2025-07-24T17:08:02.019252", "result_key": "results/1c6eedece09076be19a313df329ace357a3faf3cbc7129ca4659df4e52a06bd3/content.json", "table_keys": []}},
        return {
            "document_id": document_id,
            "metadata": doc_metadata,
            "status": parse_stage,
            "finished_at": parse_stage.get("finished_at"),
            "started_at": parse_stage.get("started_at"),
            }
    except Exception as e:
        logger.error(f"Failed to download or parse results from S3 for key {result_key}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve parsed results")


@router.post("/{document_id}/update-status", response_model=DocumentResponse)
async def update_document_status(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """
    Manually trigger a status check for a document being processed by RAGParser.
    This is useful for debugging or if a webhook fails.
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    ragparser_task_id = document.status_dict.get("stages", {}).get("parse", {}).get("result", {}).get("task_id")
    if not ragparser_task_id:
        logger.error(f"Document {document_id} has no RAGParser task ID")

        #raise HTTPException(status_code=400, detail="Document has no RAGParser task ID")
        return DocumentResponse.from_document(document)


    try:
        # Get the latest status from RAGParser
        status_response = await ragparser_client.get_task_status_new(ragparser_task_id)

        # Process the status response
        if status_response.state == "completed":
            logger.info(f"RAGParser task {ragparser_task_id} completed. Processing results...")
            await process_parsed_results(
                document_id=str(document_id),
                ragparser_status=status_response.model_dump()
            )
        elif status_response.state == "failed":
            logger.error(f"RAGParser task {ragparser_task_id} failed: {status_response.error}")
            # Update document status to failed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["parse"] = {
                **stages.get("parse", {}),
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_message": status_response.error,
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            session.add(document)
            session.commit()
        else:
            # Still pending or running, just log it
            logger.info(f"RAGParser task {ragparser_task_id} is still in progress with state: {status_response.state}")
            # Optionally update queue position or progress here if needed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["parse"] = {
                **stages.get("parse", {}),
                "queue_position": status_response.result.get("queue_position", None),
                 "progress": status_response.result.get("progress", None)
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            session.add(document)
            session.commit()

        session.refresh(document)
        return DocumentResponse.from_document(document)
    
    except TaskNotFoundError:
        logger.info(f"Task {ragparser_task_id} not found in RAGParser.")
        # The task doesn't exist, which is fine. Just return the document as is.
        return DocumentResponse.from_document(document)

    except Exception as e:
        logger.warning(f"Failed to update document status from RAGParser: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while updating status.")

async def process_parsed_results(
    document_id: str, 
    ragparser_status: Optional[Dict[str, Any]] = None
    ) -> None:
    """
    Callback function to process results after RAGParser finishes.
    This is typically called by a webhook from RAGParser.
    """
    logger.info(f"Response from RAGParser: {ragparser_status}")
    from app.core.db import engine
    result_key = ragparser_status.get("result_key")
    table_keys = ragparser_status.get("table_keys")
    try:
        with Session(engine) as session:
            document = session.get(Document, document_id)
            if not document:
                logger.error(f"Document {document_id} not found in process_parsed_results callback")
                return

            # Update parse stage status to completed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["parse"] = {
                "status": ragparser_status.get("state"),
                "started_at": ragparser_status.get("started_at"),
                "finished_at": ragparser_status.get("completed_at"),
                "result": {
                    "stage_type": "parse",
                    "parser_name": "ragparser",
                    "parser_version": ragparser_status.get("parser_used"),
                    "task_id": ragparser_status.get("task_id"),
                    #"queue_position": ragparser_status.get("queue_position"),
                    "result_key": result_key,
                    "table_keys": table_keys,
                    }
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            # RAGParser status is a dictionary with the following keys:
            #     {
            #   "state": "completed",
            #   "progress": 100,
            #   "result_key": "results/636730194f0edfbe399dfe40d5443fe9d2f2a62ba36a36a57f33ab66d49d8113/content.json",
            #   "table_keys": [],
            #   "error": null,
            #   "started_at": "2025-07-23T14:00:41.616644+00:00Z",
            #   "completed_at": "2025-07-23T17:00:51.993567Z",
            #   "parser_used": "docling-2.33.0",
            #   "pages_processed": 1,
            #   "document_info": {
            #     "table_count": 0,
            #     "image_count": 4,
            #     "text_length": 1752,
            #     "word_count": 261,
            #     "is_scanned": false,
            #     "language": "en",
            #     "rotated_pages": [],
            #     "mime_type": "application/pdf"
            #   }
            # }
            # Extract document characteristics from RAGParser results
            if "document_info" in ragparser_status:
                document_info = ragparser_status.get("document_info")
                characteristics = {}
                characteristics["page_count"] = ragparser_status.get("pages_processed", None)
                characteristics["table_count"] = document_info.get("table_count", None)
                characteristics["image_count"] = document_info.get("image_count", None)
                characteristics["text_length"] = document_info.get("text_length", None)
                characteristics["word_count"] = document_info.get("word_count", None)
                characteristics["is_scanned"] = document_info.get("is_scanned", None)
                characteristics["language"] = document_info.get("language", None)
                characteristics["rotated_pages"] = document_info.get("rotated_pages", None)
        
                # Update document metadata with new characteristics
                metadata = document.metadata_dict
                metadata.update(characteristics)
                document.metadata_dict = metadata
            
            session.add(document)
            session.commit()
            logger.info(f"Successfully processed parsed results for document {document_id}")

    except Exception as e:
        logger.error(f"Error processing parsed results for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process parsed results: {e}")



@router.delete("/{document_id}/chunks")
async def delete_document_chunks(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:admin"))],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, Any]:
    """
    Delete all chunks associated with a document.
    Also resets the 'chunk' and 'index' stage statuses.
    """
    document = session.get(Document, str(document_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Delete chunks from database
    chunk_delete_statement = delete(DocumentChunk).where(DocumentChunk.document_id == str(document_id))
    result = session.exec(chunk_delete_statement)
    deleted_count = result.rowcount
    
    # Reset chunk and index stages
    status_dict = document.status_dict
    stages = status_dict.get("stages", {})
    
    if "chunk" in stages:
        stages["chunk"] = {"status": "waiting"}
    if "index" in stages:
        stages["index"] = {"status": "waiting"}
        
    status_dict["stages"] = stages
    document.status_dict = status_dict
    
    session.add(document)
    session.commit()
    
    return {
        "message": f"Deleted {deleted_count} chunks and reset chunk/index stages for document {document_id}",
        "deleted_count": deleted_count
    }


@router.get("/{document_id}/chunks/count")
async def get_document_chunks_count(
    current_user: Annotated[User, Depends(get_user_with_permission("documents:read"))],
    document_id: uuid.UUID,
    session: SessionDep,
) -> Dict[str, Any]:
    """Get the number of chunks for a document"""
    count = session.exec(
        select(func.count(DocumentChunk.id))
        .where(DocumentChunk.document_id == str(document_id))
    ).one()
    
    return {"document_id": document_id, "chunk_count": count}

