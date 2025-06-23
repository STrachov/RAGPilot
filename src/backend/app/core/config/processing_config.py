from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class ParserType(str, Enum):
    """Supported parser types in RAGParser"""
    DOCLING = "docling"
    MARKER = "marker"
    UNSTRUCTURED = "unstructured"

class ParseConfig(BaseModel):
    """Document-specific parsing configuration"""
    parser_type: ParserType = ParserType.DOCLING
    do_ocr: bool = True
    extract_tables: bool = True
    extract_images: bool = False
    ocr_language: str = "en"
    preserve_formatting: bool = True
    handle_multi_column: bool = True
    
    class Config:
        use_enum_values = True

class ChunkConfig(BaseModel):
    """Global chunking configuration applied to all documents"""
    strategy: str = "recursive"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    preserve_table_structure: bool = True
    serialize_tables: bool = False  # Based on paper findings - this hurts performance

class IndexConfig(BaseModel):
    """Global indexing configuration applied to all documents"""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    model_type: str = "sentence-transformers"
    dimensions: int = 384
    index_type: str = "faiss"
    similarity_metric: str = "cosine"
    use_vector_db: bool = True
    use_bm25: bool = True  # Hybrid retrieval as recommended in paper
    top_n_retrieval: int = 10
    
    model_config = {"protected_namespaces": ()}

class GlobalProcessingConfig(BaseModel):
    """Global processing configuration for chunk and index stages"""
    chunk_config: ChunkConfig = Field(default_factory=ChunkConfig)
    index_config: IndexConfig = Field(default_factory=IndexConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "chunk_config": self.chunk_config.dict(),
            "index_config": self.index_config.dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalProcessingConfig":
        """Create from dictionary"""
        return cls(
            chunk_config=ChunkConfig(**data.get("chunk_config", {})),
            index_config=IndexConfig(**data.get("index_config", {}))
        )

# Default configurations
DEFAULT_PARSE_CONFIG = ParseConfig()
DEFAULT_GLOBAL_CONFIG = GlobalProcessingConfig() 