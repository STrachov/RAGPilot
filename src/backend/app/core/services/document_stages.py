from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime, timezone
import uuid
from sqlmodel import Session
from io import BytesIO
import json

from app.core.models.document import Document, DocumentChunk
from app.core.services.s3 import s3_service
from app.core.services.ragparser_client import ragparser_client
from app.core.config.settings import settings

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentStages:
    """Centralized implementation of all document processing stages"""
    
    async def parse_stage(
        self, 
        document: Document, 
        session: Session,
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle document parsing via RAGParser"""
        try:
            logger.info(f"Starting parse stage for document {document.id} with context {context}")
            
            # Generate presigned URL for RAGParser to access the document
            document_url = s3_service.get_file_url(document.file_path, expiration=3600)
            if not document_url:
                raise Exception("Failed to generate document URL for RAGParser")
            
            # Get parsing config from stage or use provided config
            stages = document.status_dict.get("stages", {})
            
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
            logger.info(f"Parse config: {parse_config}")

            # Submit document to RAGParser
            ragparser_response = await ragparser_client.submit_document_for_parsing(
                document_url=document_url,
                options={
                    "document_id": document.id,
                    "filename": document.filename,
                    "content_type": document.content_type,
                    **parse_config
                },
            )
            
            # Update document with task ID
            document.ragparser_task_id = ragparser_response.task_id
            
            # Update stage status to running
            status_dict = document.status_dict
            if "stages" not in status_dict:
                status_dict["stages"] = {}
            
            if "parse" not in status_dict["stages"]:
                status_dict["stages"]["parse"] = {"executions": []}
            elif "executions" not in status_dict["stages"]["parse"]:
                status_dict["stages"]["parse"]["executions"] = []

            status_dict["stages"]["parse"]["executions"].append({
                "stage_execution_id": stage_execution_id,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ragparser_task_id": ragparser_response.task_id,
                "pipeline_name": context.get("pipeline_name") if context else None,
            })
            
            # Set top-level status for the stage
            status_dict["stages"]["parse"]["status"] = "running"
            
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
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Handle document chunking"""
        try:
            logger.info(f"Starting chunk stage for document {document.id}")
            # Get chunking config - use provided config, document config, or global default
            stages = document.status_dict.get("stages", {})
            if config:
                chunk_config = config
            elif stages.get("chunk", {}).get("config"):
                chunk_config = stages.get("chunk", {}).get("config", {})
            else:
                # Use global default chunk config
                from app.core.services.config_service import config_service
                global_chunk_config = config_service.get_global_chunk_config()
                chunk_config = global_chunk_config.model_dump()
            logger.info(f"Chunk config: {chunk_config}")

            document_chunks = document.chunks
            if document_chunks:
                # Old chuunks should be removed
                try:
                    logger.info(f"Deleting old chunks for document {document.id}")
                    for chunk in document_chunks:
                        session.delete(chunk)
                    session.commit()
                except Exception as e:
                    logger.error(f"Error deleting old chunks for document {document.id}: {e}")

            # Process chunking - splits parsed text into chunks
            chunks = await self._create_text_chunks(document, session, chunk_config)
            
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
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle document indexing (vectorization)"""
        try:
            logger.info(f"Starting index stage for document {document.id}")
            
            # In a real implementation, this would involve a vectorization service.
            # For now, we'll simulate the process and just update the status.
            
            # If chunks are not provided, retrieve them from the document.
            if not chunks:
                chunks = document.chunks
            
            # Update stage status
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["index"] = {
                **stages.get("index", {}),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "chunks_indexed": len(chunks),
                "attempts": stages.get("index", {}).get("attempts", 0) + 1
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            
            return {"status": "completed", "chunks_indexed": len(chunks)}
        
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
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle combined chunking and indexing"""
        # This is a compound stage
        try:
            logger.info(f"Starting chunk_index stage for document {document.id}")
            
            # Run chunking
            chunks = await self.chunk_stage(document, session, config.get("chunk") if config else None)
            
            # Run indexing
            index_result = await self.index_stage(document, session, chunks, config.get("index") if config else None)
            
            return {"status": "completed", "chunks_indexed": index_result.get("chunks_indexed", 0)}
        
        except Exception as e:
            logger.error(f"Chunk_index stage failed for document {document.id}: {e}")
            raise

    async def create_graph_stage(
        self, 
        document: Document, 
        session: Session,
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a graph from the document"""
        try:
            logger.info(f"Starting graph stage for document {document.id}")
            # Placeholder for graph creation logic
            
            # Update stage status
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            stages["create_graph"] = {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
            status_dict["stages"] = stages
            document.status_dict = status_dict
            
            session.add(document)
            session.commit()
            
            return {"status": "completed"}
        except Exception as e:
            logger.error(f"Graph stage failed for document {document.id}: {e}")
            raise

    async def _create_text_chunks(
        self,
        document: Document,
        session: Session,
        chunking_config: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Create document chunks from the document's parsed text content."""
        
        # Get parsed text from S3
        parsed_data_key = document.status_dict.get("stages", {}).get("parse", {}).get("result", {}).get("result_key")
        if not parsed_data_key:
            raise Exception(f"No parsed data key found for document {document.id}")
        
        parsed_data = await ragparser_client.get_parsed_result(parsed_data_key)
        
        text_content = parsed_data.get("text_content")
        if not text_content:
            logger.warning(f"No text content found in parsed data for document {document.id}")
            return []

        # Initialize text splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunking_config.get("chunk_size", 1000),
            chunk_overlap=chunking_config.get("chunk_overlap", 200),
            length_function=len,
            add_start_index=True,
        )
        
        # Create chunks
        text_chunks = splitter.split_text(text_content)
        
        document_chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                document_id=document.id,
                text=chunk_text,
                index=i,
                metadata_json=json.dumps({"source": f"chunk_{i}"})
            )
            document_chunks.append(chunk)

        # Save chunks to database
        for chunk in document_chunks:
            session.add(chunk)
        session.commit()

        return document_chunks
    
    def _create_table_chunks(self, conversion_result, document_id: str) -> List[DocumentChunk]:
        """Creates DocumentChunk objects from table data"""
        table_chunks = []
        # Placeholder for table chunking logic
        return table_chunks

    def _table_to_markdown(self, table) -> str:
        """Converts a table object to a markdown string"""
        # Placeholder for table to markdown conversion
        return ""

# Global instance for easy import
document_stages = DocumentStages() 