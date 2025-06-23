import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.core.config.constants import DocumentStatus, DEFAULT_CHUNKING_CONFIG
from app.core.models.document import Document, DocumentChunk
from app.core.services.ragparser_client import ragparser_client
from app.core.services.s3 import s3_service
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class PipelineProcessor:
    """Service for orchestrating the complete document processing pipeline"""
    
    async def start_pipeline(self, document: Document, session) -> None:
        """
        Start the document processing pipeline
        
        This will:
        1. Generate a presigned URL for the document
        2. Submit to RAGParser for parsing
        3. Update document status and task_id
        
        Args:
            document: The document to process
            session: Database session
        """
        try:
            logger.info(f"Starting pipeline for document {document.id}")
            
            # Generate presigned URL for RAGParser to access the document
            document_url = s3_service.get_file_url(document.file_path, expiration=3600)
            if not document_url:
                raise Exception("Failed to generate document URL for RAGParser")
            
            # Submit document to RAGParser
            ragparser_response = await ragparser_client.submit_document_for_parsing(
                document_url=document_url,
                options={
                    "document_id": document.id,
                    "filename": document.filename,
                    "content_type": document.content_type
                }
            )
            
            # Update document with task ID and status
            document.ragparser_task_id = ragparser_response.task_id
            document.status = DocumentStatus.PARSING
            document.updated_at = datetime.now(timezone.utc)
            
            # Store RAGParser info in metadata
            metadata = document.metadata_dict or {}
            metadata.update({
                "ragparser_task_id": ragparser_response.task_id,
                "queue_position": ragparser_response.queue_position,
                "parsing_started_at": datetime.now(timezone.utc).isoformat()
            })
            document.metadata_dict = metadata
            
            session.add(document)
            session.commit()
            
            logger.info(f"Document {document.id} submitted to RAGParser with task_id: {ragparser_response.task_id}")
            
        except Exception as e:
            logger.error(f"Failed to start pipeline for document {document.id}: {e}")
            document.status = DocumentStatus.FAILED
            document.updated_at = datetime.now(timezone.utc)
            
            # Store error in metadata
            metadata = document.metadata_dict or {}
            metadata.update({
                "pipeline_error": str(e),
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "failed_stage": "parsing_submission"
            })
            document.metadata_dict = metadata
            
            session.add(document)
            session.commit()
            raise
    
    async def check_parsing_status(self, document: Document, session) -> bool:
        """
        Check the parsing status from RAGParser and update document accordingly
        
        Args:
            document: The document being processed
            session: Database session
            
        Returns:
            True if parsing is complete, False if still in progress
            
        Raises:
            Exception: If parsing failed or status check failed
        """
        if not document.ragparser_task_id:
            raise Exception("Document has no RAGParser task ID")
        
        try:
            # Get status from RAGParser
            status = await ragparser_client.get_task_status_new(document.ragparser_task_id)
            
            # Update metadata with latest status
            metadata = document.metadata_dict or {}
            metadata.update({
                "ragparser_status": status.state,
                "ragparser_progress": status.progress,
                "last_status_check": datetime.now(timezone.utc).isoformat()
            })
            
            if status.state == "completed":
                # Parsing completed successfully
                document.status = DocumentStatus.PARSED
                metadata.update({
                    "parsed_at": datetime.now(timezone.utc).isoformat(),
                    "result_url": status.result_key
                })
                document.metadata_dict = metadata
                document.updated_at = datetime.now(timezone.utc)
                session.add(document)
                session.commit()
                
                logger.info(f"Document {document.id} parsing completed")
                return True
                
            elif status.state == "failed":
                # Parsing failed
                document.status = DocumentStatus.FAILED
                metadata.update({
                    "failed_at": getattr(status, "failed_at", datetime.now(timezone.utc).isoformat()),
                    "failed_stage": "parsing",
                    "ragparser_error": status.error
                })
                document.metadata_dict = metadata
                document.updated_at = datetime.now(timezone.utc)
                session.add(document)
                session.commit()
                
                logger.error(f"Document {document.id} parsing failed: {status.error}")
                raise Exception(f"RAGParser processing failed: {status.error}")
                
            else:
                # Still processing (pending or processing)
                document.metadata_dict = metadata
                document.updated_at = datetime.now(timezone.utc)
                session.add(document)
                session.commit()
                
                logger.debug(f"Document {document.id} still parsing: {status.state}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to check parsing status for document {document.id}: {e}")
            
            # Update document status to failed
            document.status = DocumentStatus.FAILED
            metadata = document.metadata_dict or {}
            metadata.update({
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "failed_stage": "status_check",
                "status_check_error": str(e)
            })
            document.metadata_dict = metadata
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            raise
    
    async def process_parsed_document(self, document: Document, session) -> None:
        """
        Process the parsed document by downloading results and creating chunks
        
        Args:
            document: The document with completed parsing
            session: Database session
        """
        try:
            logger.info(f"Processing parsed document {document.id}")
            
            # Get result URL from metadata
            metadata = document.metadata_dict or {}
            result_url = metadata.get("result_url")
            if not result_url:
                raise Exception("No result URL found in document metadata")
            
            # Download parsed results from RAGParser
            parsed_data = await ragparser_client.get_parsed_result(result_url)
            
            # Update status to chunking
            document.status = DocumentStatus.CHUNKING
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            # Extract text content and create chunks
            chunks = await self._create_chunks_from_parsed_data(parsed_data, document.id)
            
            # Save chunks to database
            for chunk in chunks:
                session.add(chunk)
            
            # Update status to indexing (for now we'll mark as completed since we don't have vector indexing yet)
            document.status = DocumentStatus.COMPLETED
            document.processed_at = datetime.now(timezone.utc)
            document.updated_at = datetime.now(timezone.utc)
            
            # Update metadata with processing completion
            metadata.update({
                "chunking_completed_at": datetime.now(timezone.utc).isoformat(),
                "total_chunks": len(chunks),
                "processed_content": True
            })
            document.metadata_dict = metadata
            
            session.add(document)
            session.commit()
            
            logger.info(f"Document {document.id} processing completed with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to process parsed document {document.id}: {e}")
            
            # Update document status to failed
            document.status = DocumentStatus.FAILED
            metadata = document.metadata_dict or {}
            metadata.update({
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "failed_stage": "chunking",
                "processing_error": str(e)
            })
            document.metadata_dict = metadata
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            raise
    
    async def _create_chunks_from_parsed_data(
        self, 
        parsed_data: Dict[str, Any], 
        document_id: str
    ) -> List[DocumentChunk]:
        """
        Create document chunks from RAGParser's parsed data
        
        Args:
            parsed_data: The parsed data from RAGParser
            document_id: The document ID
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # Extract text content from parsed data
        # The exact structure depends on RAGParser's output format
        # This is a generic implementation that should be adapted
        content = parsed_data.get("content", "")
        if isinstance(content, dict):
            # If content is structured, extract text parts
            text_parts = []
            for page in content.get("pages", []):
                if isinstance(page, dict):
                    text_parts.append(page.get("text", ""))
                else:
                    text_parts.append(str(page))
            content = "\n\n".join(text_parts)
        elif not isinstance(content, str):
            content = str(content)
        
        if not content.strip():
            logger.warning(f"No content found in parsed data for document {document_id}")
            return chunks
        
        # Get chunking configuration
        chunking_config = DEFAULT_CHUNKING_CONFIG.copy()
        
        # Create text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunking_config["chunk_size"],
            chunk_overlap=chunking_config["chunk_overlap"],
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Split text into chunks
        text_chunks = text_splitter.split_text(content)
        
        # Create DocumentChunk objects
        for i, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                document_id=document_id,
                content=chunk_text,
                chunk_index=i,
            )
            
            # Set metadata
            chunk_metadata = {
                "type": "text",
                "strategy": chunking_config["strategy"],
                "chunk_size": chunking_config["chunk_size"],
                "chunk_overlap": chunking_config["chunk_overlap"],
                "source": "ragparser",
                "created_from_parsed_data": True
            }
            
            # Add any additional metadata from parsed data
            if "metadata" in parsed_data:
                chunk_metadata.update(parsed_data["metadata"])
            
            chunk.metadata_dict = chunk_metadata
            chunks.append(chunk)
        
        return chunks

# Global pipeline processor instance
pipeline_processor = PipelineProcessor() 