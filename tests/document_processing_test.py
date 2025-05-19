import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backend.app.core.services.document_processor import document_processor
from src.backend.app.core.models.document import Document, DocumentChunk

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
    test_file = Path("tests/test1.pdf")  # Specific test PDF file
    
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
    document_processor.s3_service.download_file = lambda src, dst: test_file.read_bytes() and Path(dst).write_bytes(test_file.read_bytes())
    
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

if __name__ == "__main__":
    asyncio.run(process_test_document()) 