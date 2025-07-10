from enum import Enum, auto
from typing import Dict, Any, List, Set, Optional
from pydantic import BaseModel, Field

class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


# Define permissions for each role
ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    UserRole.ADMIN: {
        # Document permissions
        "documents:create", "documents:read", "documents:update", "documents:delete",
        "documents:list:all",
        # User permissions
        "users:create", "users:read", "users:update", "users:delete", "users:list",
        # System permissions
        "system:settings", "system:logs", "system:metrics",
        # Chat permissions
        "chat:create", "chat:read", "chat:delete", "chat:advanced",
        # Config permissions
        "config:read", "config:write",
    },
    UserRole.USER: {
        # Document permissions
        "documents:create", "documents:read", "documents:update", "documents:delete",
        "documents:list:own",
        # Chat permissions
        "chat:create", "chat:read", "chat:delete",
        # User permissions (self)
        "users:read:self", "users:update:self",
    },
    UserRole.GUEST: {
        # Limited permissions
        "documents:read", "documents:list:public",
        "chat:create", "chat:read",
    }
}

class DocumentSourceType(str, Enum):
    """Document source types supported by the system"""
    PDF = "pdf"
    EMAIL = "email"
    REPORT = "report"
    SHAREPOINT = "sharepoint"
    OTHER = "other"


class PipelineStageType(str, Enum):
    """Types of pipeline stages"""
    PARSE = "parse"
    CHUNK = "chunk"
    INDEX = "index"


class DocumentStatus(str, Enum):
    """Processing status of a document"""
    PENDING = "pending"           # Document uploaded, waiting to start processing
    PARSING = "parsing"          # Document sent to RAGParser for parsing
    PARSED = "parsed"            # Document parsing completed
    CHUNKING = "chunking"        # Document being chunked
    INDEXING = "indexing"        # Document chunks being indexed
    COMPLETED = "completed"      # All processing completed successfully
    FAILED = "failed"            # Processing failed at any stage


class StageStatus(str, Enum):
    """Status of individual processing stages"""
    WAITING = "waiting"     # Stage is waiting to be started
    RUNNING = "running"     # Stage is currently processing
    COMPLETED = "completed" # Stage completed successfully
    FAILED = "failed"       # Stage failed with error
    SKIPPED = "skipped"     # Stage was skipped (e.g., already completed)



class EmbeddingModel(str, Enum):
    """Supported embedding models"""
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    COHERE = "cohere"


class IndexType(str, Enum):
    """Supported vector index types"""
    FAISS = "faiss"
    QDRANT = "qdrant"
    ELASTICSEARCH = "elasticsearch"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"


class RetrievalMethod(str, Enum):
    """Supported retrieval methods"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"


class QueryStatus(str, Enum):
    """Status of a query"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Default configurations

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
    ocr_language: str = "auto"
    preserve_formatting: bool = True
    handle_multi_column: bool = True
    
    class Config:
        use_enum_values = True


class ChunkingStrategy(str, Enum):
    """Chunking strategies for document processing"""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    RECURSIVE = "recursive"

class ChunkConfig(BaseModel):
    """Global chunking configuration applied to all documents"""
    strategy: str = ChunkingStrategy.RECURSIVE
    chunk_size: int = 1000
    chunk_overlap: int = 200
    preserve_table_structure: bool = True
    serialize_tables: bool = False  # Based on paper findings - this hurts performance


class IndexConfig(BaseModel):
    """Global indexing configuration applied to all documents"""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimensions: int = 384
    index_type: str = IndexType.FAISS
    similarity_metric: str = "cosine"
    use_vector_db: bool = True
    use_bm25: bool = True  
    top_n_retrieval: int = 10
    
    model_config = {"protected_namespaces": ()}


class GlobalProcessingConfig(BaseModel):
    """Global processing configuration for parse, chunk and index stages"""
    parse_config: ParseConfig = Field(default_factory=ParseConfig)
    chunk_config: ChunkConfig = Field(default_factory=ChunkConfig)
    index_config: IndexConfig = Field(default_factory=IndexConfig)
    default_pipeline_name: str = "standard_rag"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "parse_config": self.parse_config.model_dump(),
            "chunk_config": self.chunk_config.model_dump(),
            "index_config": self.index_config.model_dump(),
            "default_pipeline_name": self.default_pipeline_name,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalProcessingConfig":
        """Create from dictionary"""
        return cls(
            parse_config=ParseConfig(**data.get("parse_config", {})),
            chunk_config=ChunkConfig(**data.get("chunk_config", {})),
            index_config=IndexConfig(**data.get("index_config", {})),
            default_pipeline_name=data.get("default_pipeline_name", "standard_rag"),
        )


DEFAULT_RETRIEVAL_STRATEGY = {
    "method": RetrievalMethod.HYBRID,
    "top_k": 5,
    "score_threshold": 0.7,
    "semantic_weight": 0.7,
    "keyword_weight": 0.3,
}

DEFAULT_LLM_CONFIG = {
    "name": "default-llm",
    "provider": LLMProvider.OPENAI,
    "model_name": "gpt-3.5-turbo",
    "max_tokens": 1000,
    "temperature": 0.7,
}

DEFAULT_PROMPT_TEMPLATES = {
    "qa": """Answer the question based only on the following context:
{context}

Question: {query}
Answer:""",
    
    "summarize": """Summarize the following text:
{text}

Summary:"""
}
# Document processing constants
class UploadConfig(BaseModel):
    """Upload configuration"""
    max_document_size_mb: int = 50
    allowed_document_types: Dict[str, List[str]] = {
        "application/pdf": [".pdf"],
        # "application/msword": [".doc"],
        # "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
        # "text/plain": [".txt"],
        # "text/markdown": [".md"],
        # "text/csv": [".csv"],
        # "application/json": [".json"],
        # "application/vnd.ms-excel": [".xls"],
        # "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    }
