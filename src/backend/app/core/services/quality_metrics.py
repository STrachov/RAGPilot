from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ParseQualityMetrics(BaseModel):
    """Quality metrics for document parsing stage"""
    jaccard_similarity: Optional[float] = None
    term_coverage: Optional[float] = None
    table_preservation_rate: Optional[float] = None
    processing_time: Optional[float] = None
    parser_used: str
    pages_processed: int = 0
    extraction_success_rate: Optional[float] = None
    tables_extracted: int = 0
    images_extracted: int = 0
    text_length: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return self.dict(exclude_none=True)

class ChunkQualityMetrics(BaseModel):
    """Quality metrics for document chunking stage"""
    chunks_created: int = 0
    avg_chunk_size: float = 0.0
    min_chunk_size: int = 0
    max_chunk_size: int = 0
    processing_time: Optional[float] = None
    chunk_overlap_actual: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return self.dict(exclude_none=True)

class IndexQualityMetrics(BaseModel):
    """Quality metrics for document indexing stage"""
    embeddings_created: int = 0
    indexing_time: Optional[float] = None
    embedding_success_rate: Optional[float] = None
    vector_dimensions: int = 0
    index_size_mb: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return self.dict(exclude_none=True)

class QualityMetricsCalculator:
    """Utility class for calculating quality metrics"""
    
    @staticmethod
    def calculate_jaccard_similarity(text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based Jaccard similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def calculate_term_coverage(original_text: str, extracted_text: str) -> float:
        """Calculate what percentage of original terms are preserved"""
        if not original_text or not extracted_text:
            return 0.0
        
        original_terms = set(original_text.lower().split())
        extracted_terms = set(extracted_text.lower().split())
        
        if not original_terms:
            return 0.0
        
        preserved_terms = len(original_terms.intersection(extracted_terms))
        return preserved_terms / len(original_terms)
    
    @staticmethod
    def calculate_table_preservation_rate(tables_found: int, tables_expected: int) -> float:
        """Calculate table preservation rate"""
        if tables_expected == 0:
            return 1.0 if tables_found == 0 else 0.0
        
        return min(tables_found / tables_expected, 1.0)
    
    @staticmethod
    def calculate_chunk_metrics(chunks: list, target_size: int, overlap: int) -> ChunkQualityMetrics:
        """Calculate chunking quality metrics"""
        if not chunks:
            return ChunkQualityMetrics()
        
        chunk_sizes = [len(chunk) for chunk in chunks]
        
        return ChunkQualityMetrics(
            chunks_created=len(chunks),
            avg_chunk_size=sum(chunk_sizes) / len(chunk_sizes),
            min_chunk_size=min(chunk_sizes),
            max_chunk_size=max(chunk_sizes),
            chunk_overlap_actual=overlap  # This would need more sophisticated calculation
        ) 