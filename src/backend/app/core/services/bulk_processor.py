import logging
from typing import List
from sqlmodel import Session, select
from datetime import datetime, timezone

from app.core.models.document import Document
from app.core.services.dynamic_pipeline import dynamic_pipeline_service
from app.core.db import engine

logger = logging.getLogger(__name__)

class BulkProcessor:
    """Service for bulk processing operations on documents"""
    
    def __init__(self):
        self.processing = False
    
    async def reprocess_all_documents(self, session: Session = None) -> bool:
        """
        Reprocess all documents by running the 'standard_rag' pipeline.
        This will automatically handle dependencies and skip completed stages.
        """
        if self.processing:
            logger.warning("Bulk reprocessing already in progress")
            return False
        
        self.processing = True
        
        try:
            if session is None:
                session = Session(engine)
                should_close = True
            else:
                should_close = False
            
            statement = select(Document)
            documents = session.exec(statement).all()
            
            logger.info(f"Starting bulk reprocessing for {len(documents)} documents using 'standard_rag' pipeline")
            
            processed_count = 0
            for document in documents:
                try:
                    await dynamic_pipeline_service.execute_pipeline(
                        pipeline_name="standard_rag",
                        document_id=document.id,
                        session=session
                    )
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error reprocessing document {document.id} with pipeline: {e}")
                    continue
            
            logger.info(f"Bulk reprocessing completed for {processed_count} documents")
            
            if should_close:
                session.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error during bulk reprocessing: {e}")
            return False
        finally:
            self.processing = False
    
    def is_processing(self) -> bool:
        """Check if bulk processing is currently running"""
        return self.processing
    
    async def reprocess_documents_by_ids(self, document_ids: List[str], session: Session = None) -> int:
        """
        Reprocess specific documents by their IDs using the 'standard_rag' pipeline.
        """
        try:
            if session is None:
                session = Session(engine)
                should_close = True
            else:
                should_close = False
            
            statement = select(Document).where(Document.id.in_(document_ids))
            documents = session.exec(statement).all()
            
            logger.info(f"Reprocessing {len(documents)} documents by IDs using 'standard_rag' pipeline")
            
            processed_count = 0
            for document in documents:
                try:
                    await dynamic_pipeline_service.execute_pipeline(
                        pipeline_name="standard_rag",
                        document_id=document.id,
                        session=session
                    )
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error reprocessing document {document.id} with pipeline: {e}")
                    continue
            
            if should_close:
                session.close()
            
            logger.info(f"Successfully reprocessed {processed_count} documents")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error during selective reprocessing: {e}")
            return 0

# Global instance
bulk_processor = BulkProcessor() 