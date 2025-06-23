import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.services.document_processor import document_processor
from app.core.models.document import Document, DocumentChunk
from app.core.services.s3 import s3_service

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock database session for testing
class MockSession:
    def __init__(self):
        self.items = []
    
    def add(self, item):
        self.items.append(item)
        logger.info(f"Added {type(item).__name__} to session")
    
    def commit(self):
        logger.info(f"Committed {len(self.items)} items to session")
    
    def get(self, model, id):
        logger.info(f"Getting {model.__name__} with ID {id}")
        for item in self.items:
            if isinstance(item, model) and item.id == id:
                return item
        return None

async def process_test_document():
    """Test processing a document with the enhanced Docling processor"""
    # Create a test document
    doc_id = "test-document-id"
    test_file = Path(__file__).parent / "test1.pdf"
    logger.info(f"Starting test...")
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return
    
    logger.info(f"Processing test document: {test_file}")
    
    # Create mock document
    document = Document(
        id=doc_id,
        filename=test_file.name,
        title="Test Document",
        file_path=str(test_file),
        content_type="application/pdf",
        file_size=test_file.stat().st_size,
    )
    
    # Create mock session
    session = MockSession()
    session.add(document)
    
    # Create a minimal S3 service mock to avoid S3 downloads
    # Mock the s3_service download_file function directly
    original_download_file = s3_service.download_file
    s3_service.download_file = lambda src, dst: Path(dst).write_bytes(test_file.read_bytes()) or True
    
    # Patch the _extract_document_metadata method to handle missing time_elapsed
    original_extract_metadata = document_processor._extract_document_metadata
    
    def patched_extract_metadata(conversion_result):
        """Patched version of _extract_document_metadata that doesn't rely on time_elapsed"""
        doc = conversion_result.document
        
        # Basic metadata without time_elapsed
        metadata = {
            "page_count": len(doc.pages),
            "has_tables": len(doc.tables) > 0,
            "table_count": len(doc.tables),
            "has_images": len(getattr(doc, "pictures", [])) > 0,
            "processing_time": 0  # Use default value
        }
        
        # Add any document metadata if available
        if hasattr(doc, "metadata") and doc.metadata:
            metadata.update(doc.metadata)
            
        return metadata
    
    # Apply the patch
    document_processor._extract_document_metadata = patched_extract_metadata
    
    # Process the document
    try:
        chunks = await document_processor.process_document(document, session)
        
        # Summarize results
        text_chunks = [c for c in chunks if c.metadata_dict.get("type") == "text"]
        table_chunks = [c for c in chunks if c.metadata_dict.get("type") == "table"]
        
        logger.info(f"Document processing completed successfully")
        logger.info(f"Total chunks: {len(chunks)}")
        logger.info(f"Text chunks: {len(text_chunks)}")
        logger.info(f"Table chunks: {len(table_chunks)}")
        
        # Print sample of first text chunk
        if text_chunks:
            content = text_chunks[0].content
            logger.info(f"Sample text chunk (first 100 chars): {content[:100]}...")
        
        # Print sample of first table chunk
        if table_chunks:
            content = table_chunks[0].content
            logger.info(f"Sample table chunk: \n{content}")
        
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
    finally:
        # Restore the original methods
        s3_service.download_file = original_download_file
        document_processor._extract_document_metadata = original_extract_metadata

if __name__ == "__main__":
    asyncio.run(process_test_document()) 