import logging
from typing import List
from sqlmodel import Session, select
from datetime import datetime, timezone

from app.core.models.document import Document
from app.core.services.config_service import config_service
from app.core.db import engine

logger = logging.getLogger(__name__)

class BulkProcessor:
    """Service for bulk processing operations on documents"""
    
    def __init__(self):
        self.processing = False
    
    async def reprocess_all_documents(self, session: Session = None) -> bool:
        """
        Reprocess all documents with current global configuration
        This will reset chunk and index stages to waiting and trigger reprocessing
        
        Args:
            session: Database session (optional, will create new if not provided)
            
        Returns:
            bool: True if bulk reprocessing was initiated successfully
        """
        if self.processing:
            logger.warning("Bulk reprocessing already in progress")
            return False
        
        self.processing = True
        
        try:
            # Use provided session or create new one
            if session is None:
                session = Session(engine)
                should_close = True
            else:
                should_close = False
            
            # Get all documents
            statement = select(Document)
            documents = session.exec(statement).all()
            
            logger.info(f"Starting bulk reprocessing for {len(documents)} documents")
            
            # Get current global configuration
            global_config = config_service.get_global_config()
            
            # Update each document's status to trigger reprocessing
            updated_count = 0
            for document in documents:
                try:
                    # Update document status to reset chunk and index stages
                    status_data = document.status_dict
                    
                    # Reset chunk and index stages to waiting
                    if "stages" in status_data:
                        # Only reset if parse stage is completed
                        if status_data["stages"].get("parse", {}).get("status") == "completed":
                            status_data["stages"]["chunk"] = {
                                "status": "waiting",
                                "metrics": {}
                            }
                            status_data["stages"]["index"] = {
                                "status": "waiting", 
                                "metrics": {}
                            }
                            
                            # Update current stage to chunk if parse is done
                            status_data["current_stage"] = "chunk"
                            status_data["stage_status"] = "waiting"
                            
                            document.status_dict = status_data
                            document.updated_at = datetime.now(timezone.utc)
                            
                            session.add(document)
                            updated_count += 1
                        else:
                            logger.debug(f"Skipping document {document.id} - parse stage not completed")
                    
                except Exception as e:
                    logger.error(f"Error updating document {document.id}: {e}")
                    continue
            
            # Commit all changes
            session.commit()
            
            logger.info(f"Bulk reprocessing initiated for {updated_count} documents")
            
            # Close session if we created it
            if should_close:
                session.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error during bulk reprocessing: {e}")
            if session:
                session.rollback()
            return False
        finally:
            self.processing = False
    
    def is_processing(self) -> bool:
        """Check if bulk processing is currently running"""
        return self.processing
    
    async def reprocess_documents_by_ids(self, document_ids: List[str], session: Session = None) -> int:
        """
        Reprocess specific documents by their IDs
        
        Args:
            document_ids: List of document IDs to reprocess
            session: Database session (optional)
            
        Returns:
            int: Number of documents successfully queued for reprocessing
        """
        try:
            # Use provided session or create new one
            if session is None:
                session = Session(engine)
                should_close = True
            else:
                should_close = False
            
            # Get documents by IDs
            statement = select(Document).where(Document.id.in_(document_ids))
            documents = session.exec(statement).all()
            
            logger.info(f"Reprocessing {len(documents)} specific documents")
            
            updated_count = 0
            for document in documents:
                try:
                    # Reset chunk and index stages
                    status_data = document.status_dict
                    
                    if "stages" in status_data:
                        # Only reset if parse stage is completed
                        if status_data["stages"].get("parse", {}).get("status") == "completed":
                            status_data["stages"]["chunk"] = {
                                "status": "waiting",
                                "metrics": {}
                            }
                            status_data["stages"]["index"] = {
                                "status": "waiting",
                                "metrics": {}
                            }
                            
                            status_data["current_stage"] = "chunk"
                            status_data["stage_status"] = "waiting"
                            
                            document.status_dict = status_data
                            document.updated_at = datetime.now(timezone.utc)
                            
                            session.add(document)
                            updated_count += 1
                
                except Exception as e:
                    logger.error(f"Error updating document {document.id}: {e}")
                    continue
            
            session.commit()
            
            # Close session if we created it
            if should_close:
                session.close()
            
            logger.info(f"Successfully queued {updated_count} documents for reprocessing")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error during selective reprocessing: {e}")
            if session:
                session.rollback()
            return 0

# Global instance
bulk_processor = BulkProcessor() 