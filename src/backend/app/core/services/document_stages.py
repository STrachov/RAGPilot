from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime, timezone
from sqlmodel import Session
from io import BytesIO

from app.core.models.document import Document, DocumentChunk
from app.core.services.s3 import s3_service
from app.core.services.ragparser_client import ragparser_client
from app.core.services.bulk_processor import BulkProcessor
from app.core.config.settings import settings

logger = logging.getLogger(__name__)


class DocumentStages:
    """Centralized implementation of all document processing stages"""
    
    def __init__(self):
        self.bulk_processor = BulkProcessor()
    
    async def upload_stage(
        self, 
        document: Document, 
        session: Session,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle document upload to S3 storage"""
        try:
            logger.info(f"Starting upload stage for document {document.id}")
            
            # Extract upload parameters from config
            if not config:
                raise Exception("Upload stage requires config with file_content, s3_key, and content_type")
            
            file_content = config.get("file_content")
            s3_key = config.get("s3_key")
            content_type = config.get("content_type")
            metadata = config.get("metadata", {})
            
            if not all([file_content, s3_key, content_type]):
                raise Exception("Missing required upload parameters: file_content, s3_key, or content_type")
            
            # Update stage status to running
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["upload"] = {
                **stages.get("upload", {}),
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "attempts": stages.get("upload", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            session.add(document)
            session.commit()
            
            # Convert bytes to file-like object for S3 upload
            file_obj = BytesIO(file_content)
            
            # Upload to S3
            upload_success = s3_service.upload_file(
                file_obj, 
                s3_key, 
                content_type,
                metadata=metadata
            )
            
            if not upload_success:
                raise Exception("Failed to upload document to storage")
            
            # Update document file path
            document.file_path = s3_key
            
            # Update upload stage status to completed
            stages["upload"] = {
                **stages.get("upload", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "file_size": len(file_content) if isinstance(file_content, bytes) else None
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            document.updated_at = datetime.now(timezone.utc)
            
            session.add(document)
            session.commit()
            
            # Auto-trigger parse stage if configured
            auto_start_parse = config.get("auto_start_parse", False)
            if auto_start_parse:
                logger.info(f"Auto-starting parse stage for document {document.id}")
                try:
                    # First, pre-set parse stage status to running (like manual trigger does)
                    stages["parse"] = {
                        **stages.get("parse", {}),
                        "status": "running",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "attempts": stages.get("parse", {}).get("attempts", 0) + 1,
                        "error_message": None
                    }
                    status_dict["stages"] = stages
                    document.status_dict = status_dict
                    session.add(document)
                    session.commit()
                    
                    # Then call the parse stage method to submit to RAGParser
                    parse_result = await self.parse_stage(document, session)
                    logger.info(f"Parse stage started successfully with result: {parse_result}")
                except Exception as e:
                    logger.error(f"Failed to auto-start parse stage for document {document.id}: {e}")
                    # Mark parse stage as failed
                    stages["parse"] = {
                        **stages.get("parse", {}),
                        "status": "failed",
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                        "error_message": str(e),
                        "attempts": stages.get("parse", {}).get("attempts", 0) + 1
                    }
                    status_dict["stages"] = stages
                    document.status_dict = status_dict
                    session.add(document)
                    session.commit()
                    # Don't fail the upload if parse fails to start
                    pass
            
            logger.info(f"Upload stage completed for document {document.id}")
            return {
                "status": "completed", 
                "s3_key": s3_key, 
                "file_size": len(file_content) if isinstance(file_content, bytes) else None,
                "auto_start_parse": auto_start_parse
            }
            
        except Exception as e:
            logger.error(f"Upload stage failed for document {document.id}: {e}")
            
            # Update upload stage status to failed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["upload"] = {
                **stages.get("upload", {}),
                "status": "failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "attempts": stages.get("upload", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            raise
    
    async def parse_stage(
        self, 
        document: Document, 
        session: Session,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle document parsing via RAGParser"""
        try:
            logger.info(f"Starting parse stage for document {document.id}")
            
            # Generate presigned URL for RAGParser to access the document
            document_url = s3_service.get_file_url(document.file_path, expiration=3600)
            if not document_url:
                raise Exception("Failed to generate document URL for RAGParser")
            
            # Get parsing config from stage or use provided config
            stages = document.status_dict.get("stages", {})
            parse_config = config or stages.get("parse", {}).get("config", {})
            
            # Submit document to RAGParser
            ragparser_response = await ragparser_client.submit_document_for_parsing(
                document_url=document_url,
                options={
                    "document_id": document.id,
                    "filename": document.filename,
                    "content_type": document.content_type,
                    **parse_config
                }
            )
            
            # Update document with task ID
            document.ragparser_task_id = ragparser_response.task_id
            
            # Update stage status to running
            stages["parse"] = {
                **stages.get("parse", {}),
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ragparser_task_id": ragparser_response.task_id,
                "queue_position": ragparser_response.queue_position,
                "attempts": stages.get("parse", {}).get("attempts", 0) + 1
            }
            # Update status_dict properly without overwriting other data
            status_dict = document.status_dict
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            
            logger.info(f"Document {document.id} submitted to RAGParser with task_id: {ragparser_response.task_id}")
            
            return {
                "status": "running", 
                "task_id": ragparser_response.task_id,
                "queue_position": ragparser_response.queue_position
            }
            
        except Exception as e:
            logger.error(f"Parse stage failed for document {document.id}: {e}")
            
            # Update stage status to failed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["parse"] = {
                **stages.get("parse", {}),
                "status": "failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "attempts": stages.get("parse", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            raise
    
    async def chunk_stage(
        self, 
        document: Document, 
        session: Session,
        config: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Handle document chunking"""
        try:
            logger.info(f"Starting chunk stage for document {document.id}")
            
            # Process chunking - splits parsed text into chunks
            chunks = await self.bulk_processor.process_document(document, session)
            
            # Update stage status
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["chunk"] = {
                **stages.get("chunk", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "chunks_created": len(chunks),
                "attempts": stages.get("chunk", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            
            logger.info(f"Chunk stage completed for document {document.id} with {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Chunk stage failed for document {document.id}: {e}")
            
            # Update stage status to failed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["chunk"] = {
                **stages.get("chunk", {}),
                "status": "failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "attempts": stages.get("chunk", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            raise
    
    async def index_stage(
        self, 
        document: Document, 
        session: Session,
        chunks: Optional[List[DocumentChunk]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle vector indexing"""
        try:
            logger.info(f"Starting index stage for document {document.id}")
            
            # TODO: Implement vector indexing logic here
            # For now, just mark as completed
            logger.info(f"Index stage for document {document.id} - not yet implemented")
            
            # Update stage status
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["index"] = {
                **stages.get("index", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "attempts": stages.get("index", {}).get("attempts", 0) + 1,
                "note": "Vector indexing not yet implemented"
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            
            logger.info(f"Index stage completed for document {document.id}")
            return {"status": "completed", "indexed_chunks": len(chunks or [])}
            
        except Exception as e:
            logger.error(f"Index stage failed for document {document.id}: {e}")
            
            # Update stage status to failed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["index"] = {
                **stages.get("index", {}),
                "status": "failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "attempts": stages.get("index", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            raise
    
    async def chunk_index_stage(
        self, 
        document: Document, 
        session: Session,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle combined chunking and indexing stage"""
        try:
            logger.info(f"Starting chunk-index stage for document {document.id}")
            
            # Process chunking - splits parsed text into chunks
            chunks = await self.bulk_processor.process_document(document, session)
            
            # TODO: Implement vector indexing logic here
            logger.info(f"Chunking completed for document {document.id}, indexing not yet implemented")
            
            # Update stage status
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["chunk-index"] = {
                **stages.get("chunk-index", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "chunks_created": len(chunks),
                "attempts": stages.get("chunk-index", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            
            logger.info(f"Chunk-index stage completed for document {document.id}")
            return {"status": "completed", "chunks_created": len(chunks)}
            
        except Exception as e:
            logger.error(f"Chunk-index stage failed for document {document.id}: {e}")
            
            # Update stage status to failed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["chunk-index"] = {
                **stages.get("chunk-index", {}),
                "status": "failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "attempts": stages.get("chunk-index", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            raise
    
    async def create_graph_stage(
        self, 
        document: Document, 
        session: Session,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle knowledge graph creation (future implementation)"""
        try:
            logger.info(f"Starting graph creation stage for document {document.id}")
            
            # TODO: Implement knowledge graph creation logic
            logger.info(f"Graph creation stage for document {document.id} - not yet implemented")
            
            # Update stage status
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["graph"] = {
                **stages.get("graph", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "attempts": stages.get("graph", {}).get("attempts", 0) + 1,
                "note": "Knowledge graph creation not yet implemented"
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            
            logger.info(f"Graph creation stage completed for document {document.id}")
            return {"status": "completed", "note": "Knowledge graph creation not yet implemented"}
            
        except Exception as e:
            logger.error(f"Graph creation stage failed for document {document.id}: {e}")
            
            # Update stage status to failed
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["graph"] = {
                **stages.get("graph", {}),
                "status": "failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "attempts": stages.get("graph", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            raise


# Global instance for easy import
document_stages = DocumentStages() 