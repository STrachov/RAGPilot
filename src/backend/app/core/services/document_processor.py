from typing import List, Dict, Any, Optional, Tuple
import os
import tempfile
import logging
import json
from pathlib import Path
from datetime import datetime, timezone

from docling.document_converter import DocumentConverter, FormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, EasyOcrOptions
from docling.datamodel.base_models import InputFormat, ConversionStatus
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config.constants import DocumentStatus, ChunkingStrategy, DEFAULT_CHUNKING_CONFIG
from app.core.models.document import Document, DocumentChunk
from app.core.services.s3 import s3_service

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Service for processing documents using Docling"""
    
    def __init__(self):
        """Initialize document processor with Docling converter"""
        self.converter = self._create_document_converter()
        
    def _create_document_converter(self) -> DocumentConverter:
        """Creates and returns a DocumentConverter with optimized pipeline options"""
        # Configure advanced PDF processing options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True  # Enable OCR for scanned documents
        pipeline_options.ocr_options = EasyOcrOptions(lang=['en'], force_full_page_ocr=False) 
        pipeline_options.do_table_structure = True  # Extract table structure
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        
        # Define format options for PDF processing
        format_options = {
            InputFormat.PDF: FormatOption(
                pipeline_cls=StandardPdfPipeline,
                pipeline_options=pipeline_options,
                backend=DoclingParseV2DocumentBackend
            )
        }
        
        return DocumentConverter(format_options=format_options)
        
    async def process_document(self, document: Document, session) -> List[DocumentChunk]:
        """
        Process a document using Docling
        
        Args:
            document: The document to process
            session: Database session
            
        Returns:
            List of document chunks created
        """
        try:
            # Update document status
            document.status = DocumentStatus.PROCESSING
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            # Download document from S3 to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(document.filename).suffix) as temp_file:
                temp_path = temp_file.name
                
            download_success = s3_service.download_file(document.file_path, temp_path)
            if not download_success:
                raise Exception(f"Failed to download file from S3: {document.file_path}")
            
            # Process document with Docling
            conversion_result = self.converter.convert(temp_path)
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")
            
            # Check if conversion was successful
            if conversion_result.status != ConversionStatus.SUCCESS:
                raise Exception(f"Document conversion failed: {conversion_result.status}")
                
            # Store document metadata
            doc_metadata = self._extract_document_metadata(conversion_result)
            document.metadata_dict = doc_metadata
            
            # Process document content with enhanced chunking
            chunks = []
            
            # Extract and process text content
            document_text = conversion_result.document.export_to_markdown()
            text_chunks = self._create_text_chunks(document_text, document.id)
            chunks.extend(text_chunks)
            
            # Process tables if available
            table_chunks = self._process_tables(conversion_result, document.id)
            chunks.extend(table_chunks)
            
            # Save chunks to database
            for chunk in chunks:
                session.add(chunk)
            
            # Update document status
            document.status = DocumentStatus.INDEXED
            document.processed_at = datetime.now(timezone.utc)
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {e}")
            document.status = DocumentStatus.FAILED
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            session.commit()
            raise
    
    def _extract_document_metadata(self, conversion_result) -> Dict[str, Any]:
        """Extract metadata from the Docling conversion result"""
        doc = conversion_result.document
        
        # Basic metadata
        metadata = {
            "page_count": len(doc.pages),
            "has_tables": len(doc.tables) > 0,
            "table_count": len(doc.tables),
            "has_images": len(getattr(doc, "pictures", [])) > 0,
            "processing_time": conversion_result.time_elapsed
        }
        
        # Add any document metadata if available
        if hasattr(doc, "metadata") and doc.metadata:
            metadata.update(doc.metadata)
            
        return metadata
    
    def _create_text_chunks(self, text: str, document_id: str) -> List[DocumentChunk]:
        """
        Create document chunks from the extracted text using the configured chunking strategy
        
        Args:
            text: The extracted document text
            document_id: The ID of the document
            
        Returns:
            List of DocumentChunk objects
        """
        # Get chunking configuration
        chunking_config = DEFAULT_CHUNKING_CONFIG.copy()
        
        # Create chunks using the specified strategy
        strategy = chunking_config["strategy"]
        chunks = []
        
        # Create text splitter with appropriate configuration
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunking_config["chunk_size"],
            chunk_overlap=chunking_config["chunk_overlap"],
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Split text into chunks
        text_chunks = text_splitter.split_text(text)
            
        # Create DocumentChunk objects
        for i, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                document_id=document_id,
                content=chunk_text,
                chunk_index=i,
            )
            # Set metadata using the proper property
            chunk.metadata_dict = {
                "type": "text",
                "strategy": strategy,
                "chunk_size": chunking_config["chunk_size"],
                "chunk_overlap": chunking_config["chunk_overlap"],
            }
            chunks.append(chunk)
            
        return chunks
        
    def _process_tables(self, conversion_result, document_id: str) -> List[DocumentChunk]:
        """Process tables from the Docling conversion result"""
        chunks = []
        doc = conversion_result.document
        
        # Process each table
        for i, table in enumerate(doc.tables):
            # Get table as markdown
            try:
                table_md = self._table_to_markdown(table)
                
                # Create chunk for this table
                chunk = DocumentChunk(
                    document_id=document_id,
                    content=table_md,
                    chunk_index=len(chunks),  # Use the current length as the index
                )
                
                # Find page number if available
                page_num = None
                if hasattr(table, "prov") and table.prov and len(table.prov) > 0:
                    page_num = table.prov[0].get("page_no")
                
                # Set metadata
                chunk.metadata_dict = {
                    "type": "table",
                    "table_index": i,
                    "page": page_num,
                    "rows": table.data.get("num_rows", 0) if hasattr(table, "data") else 0,
                    "columns": table.data.get("num_cols", 0) if hasattr(table, "data") else 0
                }
                
                chunks.append(chunk)
            except Exception as e:
                logger.warning(f"Error processing table {i}: {e}")
                
        return chunks
        
    def _table_to_markdown(self, table) -> str:
        """Convert a Docling table to markdown format"""
        from tabulate import tabulate
        
        # Extract table data
        table_data = []
        
        # Check if table has the expected structure
        if hasattr(table, "data") and "grid" in table.data:
            # Extract rows from grid
            for row in table.data["grid"]:
                table_row = [cell.get("text", "") for cell in row]
                table_data.append(table_row)
            
            # Use first row as header if available
            if len(table_data) > 1:
                try:
                    md_table = tabulate(
                        table_data[1:], 
                        headers=table_data[0], 
                        tablefmt="github"
                    )
                except:
                    # Fallback if header row has issues
                    md_table = tabulate(table_data, tablefmt="github")
            else:
                md_table = tabulate(table_data, tablefmt="github")
        else:
            # Handle tables with different structure
            if hasattr(table, "export_to_markdown"):
                return table.export_to_markdown()
            else:
                return str(table)
                
        return md_table


# Create singleton instance
document_processor = DocumentProcessor() 