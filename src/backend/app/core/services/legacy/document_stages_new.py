import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.core.db import engine
from app.core.models.document import Document
from app.core.config.settings import settings
from app.core.logger import app_logger as logger

class DocumentStagesService:
    """Service for managing document processing stages"""
    
    def __init__(self):
        pass
    
    async def upload_stage(self, document: Document, session: Session, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process the upload stage
        
        Args:
            document: Document to process
            session: Database session
            config: Optional configuration overrides
            
        Returns:
            Dict with stage result information
        """
        try:
            logger.info(f"Processing upload stage for document {document.id}")
            
            # Get the stages dictionary
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            
            # Update upload stage status
            stages["upload"] = {
                **stages.get("upload", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "file_size": document.file_size,
                "content_type": document.content_type
            }
            
            # Update the document status
            status_dict["stages"] = stages
            document.status_dict = status_dict
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            logger.info(f"Upload stage completed for document {document.id}")
            
            return {
                "status": "completed",
                "message": "Upload stage completed successfully",
                "file_size": document.file_size
            }
            
        except Exception as e:
            logger.error(f"Upload stage failed for document {document.id}: {e}")
            raise
    
    async def parse_stage(self, document: Document, session: Session, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process the parse stage using RAGParser microservice
        
        Args:
            document: Document to process
            session: Database session
            config: Optional parsing configuration overrides
            
        Returns:
            Dict with stage result information
        """
        try:
            logger.info(f"Processing parse stage for document {document.id}")
            
            # Import services here to avoid circular imports
            from app.core.services.ragparser_client import ragparser_client
            from app.core.services.s3 import s3_service
            
            # Get the stages dictionary
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            
            # Get parsing config - use provided config, document config, or global default
            if config:
                parse_config = config
            elif stages.get("parse", {}).get("config"):
                parse_config = stages.get("parse", {}).get("config", {})
            else:
                # Use global default parse config
                from app.core.services.config_service import config_service
                global_parse_config = config_service.get_global_parse_config()
                parse_config = global_parse_config.model_dump()
            
            # Generate presigned URL for RAGParser
            document_url = s3_service.get_file_url(document.file_path, expiration=3600)
            if not document_url:
                raise Exception("Failed to generate document URL for RAGParser")
            
            # Submit to RAGParser
            ragparser_response = await ragparser_client.submit_document_for_parsing(
                document_url=document_url,
                parse_config=parse_config,
                options={
                    "document_id": document.id,
                    "filename": document.filename,
                    "content_type": document.content_type
                }
            )
            
            # Update parse stage status
            stages["parse"] = {
                **stages.get("parse", {}),
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ragparser_task_id": ragparser_response.task_id,
                "queue_position": ragparser_response.queue_position,
                "config": parse_config
            }
            
            # Update the document status
            status_dict["stages"] = stages
            document.status_dict = status_dict
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            logger.info(f"Parse stage started for document {document.id} with task_id: {ragparser_response.task_id}")
            
            return {
                "status": "running",
                "message": "Parse stage started successfully",
                "task_id": ragparser_response.task_id,
                "queue_position": ragparser_response.queue_position
            }
            
        except Exception as e:
            logger.error(f"Parse stage failed for document {document.id}: {e}")
            raise
    
    async def chunk_stage(self, document: Document, session: Session, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process the chunk stage - splits parsed text into chunks
        
        Args:
            document: Document to process  
            session: Database session
            config: Optional chunking configuration overrides
            
        Returns:
            Dict with stage result information
        """
        try:
            logger.info(f"Processing chunk stage for document {document.id}")
            
            # Import chunking service here to avoid circular imports
            from app.core.services.document_processor import document_processor
            
            # Get the stages dictionary
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            
            # Get chunking config - use provided config, document config, or global default
            if config:
                chunk_config = config
            elif stages.get("chunk", {}).get("config"):
                chunk_config = stages.get("chunk", {}).get("config", {})
            else:
                # Use global default chunk config
                from app.core.services.config_service import config_service
                global_chunk_config = config_service.get_global_chunk_config()
                chunk_config = global_chunk_config.model_dump()
            
            # Process the document to create chunks
            chunks = await document_processor.process_document(document, session, chunk_config)
            
            # Update chunk stage status
            stages["chunk"] = {
                **stages.get("chunk", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "chunks_created": len(chunks),
                "config": chunk_config
            }
            
            # Update the document status
            status_dict["stages"] = stages
            document.status_dict = status_dict
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            logger.info(f"Chunk stage completed for document {document.id}, created {len(chunks)} chunks")
            
            return {
                "status": "completed",
                "message": "Chunk stage completed successfully",
                "chunks_created": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Chunk stage failed for document {document.id}: {e}")
            raise
    
    async def index_stage(self, document: Document, session: Session, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process the index stage - creates vector embeddings and indexes
        
        Args:
            document: Document to process
            session: Database session  
            config: Optional indexing configuration overrides
            
        Returns:
            Dict with stage result information
        """
        try:
            logger.info(f"Processing index stage for document {document.id}")
            
            # Get the stages dictionary
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            
            # Get indexing config - use provided config, document config, or global default
            if config:
                index_config = config
            elif stages.get("index", {}).get("config"):
                index_config = stages.get("index", {}).get("config", {})
            else:
                # Use global default index config
                from app.core.services.config_service import config_service
                global_index_config = config_service.get_global_index_config()
                index_config = global_index_config.model_dump()
            
            # TODO: Implement actual vector indexing logic
            # For now, just mark as completed
            logger.info(f"Indexing stage for document {document.id} - implementation pending")
            
            # Update index stage status
            stages["index"] = {
                **stages.get("index", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "config": index_config
            }
            
            # Update the document status
            status_dict["stages"] = stages
            document.status_dict = status_dict
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            logger.info(f"Index stage completed for document {document.id}")
            
            return {
                "status": "completed",
                "message": "Index stage completed successfully",
                "note": "Vector indexing implementation pending"
            }
            
        except Exception as e:
            logger.error(f"Index stage failed for document {document.id}: {e}")
            raise

    async def check_parse_status(self, document: Document, session: Session) -> Dict[str, Any]:
        """
        Check the status of parsing for a document
        
        Args:
            document: Document to check
            session: Database session
            
        Returns:
            Dict with updated status information
        """
        try:
            # Import here to avoid circular imports
            from app.core.services.ragparser_client import ragparser_client
            
            # Get the stages dictionary
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            parse_stage = stages.get("parse", {})
            
            # Get task ID from parse stage
            task_id = parse_stage.get("ragparser_task_id")
            if not task_id:
                raise Exception("No RAGParser task ID found")
            
            # Check status with RAGParser
            status = await ragparser_client.get_parsing_status(task_id)
            
            # Update parse stage based on status
            if status.state == "completed":
                parse_stage.update({
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "result": {
                        "result_key": status.result_key,
                        "table_keys": getattr(status, 'table_keys', []),
                        "pages_processed": getattr(status, 'pages_processed', None)
                    }
                })
                
                # Store document analysis in metadata
                metadata = document.metadata_dict or {}
                if hasattr(status, 'document_info') and status.document_info:
                    structure_info = {
                        "page_count": getattr(status, 'pages_processed', None),
                        "analysis_source": "ragparser"
                    }
                    metadata["structure"] = structure_info
                    document.metadata_dict = metadata
                
            elif status.state == "failed":
                parse_stage.update({
                    "status": "failed",
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": status.error
                })
            else:
                parse_stage.update({
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "queue_position": getattr(status, 'queue_position', None)
                })
            
            # Update document
            stages["parse"] = parse_stage
            status_dict["stages"] = stages
            document.status_dict = status_dict
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            return {
                "status": parse_stage.get("status"),
                "state": status.state,
                "updated": True
            }
            
        except Exception as e:
            logger.error(f"Failed to check parse status for document {document.id}: {e}")
            raise

# Global instance for easy import
document_stages = DocumentStagesService() 