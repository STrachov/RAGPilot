from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field


class RetrievalMethod(str, Enum):
    """Supported retrieval methods"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class RetrievalStrategy(SQLModel):
    """Configuration for retrieval strategy"""
    method: RetrievalMethod = RetrievalMethod.HYBRID
    top_k: int = 5
    score_threshold: Optional[float] = 0.7
    
    # Semantic search parameters
    semantic_weight: Optional[float] = 0.7
    
    # Keyword search parameters
    keyword_weight: Optional[float] = 0.3
    
    # Advanced parameters
    reranking_enabled: bool = False
    reranking_model: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None


class RetrievalConfig(SQLModel):
    """Model for retrieval configuration"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    strategy: RetrievalStrategy
    index_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None 