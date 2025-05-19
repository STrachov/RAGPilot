from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field


class ChunkingStrategy(str, Enum):
    """Chunking strategies for document processing"""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    RECURSIVE = "recursive"


class ChunkingConfig(SQLModel):
    """Configuration for document chunking"""
    strategy: ChunkingStrategy
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: Optional[List[str]] = None
    additional_params: Optional[Dict[str, Any]] = None


class EmbeddingModel(str, Enum):
    """Supported embedding models"""
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    COHERE = "cohere"
 

class EmbeddingConfig(SQLModel):
    """Configuration for embeddings"""
    model_name: str
    model_type: EmbeddingModel
    dimensions: int
    api_key: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None


class IndexType(str, Enum):
    """Supported vector index types"""
    FAISS = "faiss"
    QDRANT = "qdrant"
    ELASTICSEARCH = "elasticsearch"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"


class IndexConfig(SQLModel):
    """Configuration for vector indexes"""
    name: str
    index_type: IndexType
    dimensions: int
    similarity_metric: str = "cosine"
    connection_params: Optional[Dict[str, Any]] = None
    additional_params: Optional[Dict[str, Any]] = None


class Pipeline(SQLModel):
    """Model for processing pipeline configuration"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    chunking_config_id: str
    embedding_config_id: str
    index_config_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None 