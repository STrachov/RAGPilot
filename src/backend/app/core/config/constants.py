from enum import Enum, auto
from typing import Dict, Any, List, Set


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


class DocumentStatus(str, Enum):
    """Processing status of a document"""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class ChunkingStrategy(str, Enum):
    """Chunking strategies for document processing"""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    RECURSIVE = "recursive"


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

DEFAULT_CHUNKING_CONFIG = {
    "strategy": ChunkingStrategy.PARAGRAPH,
    "chunk_size": 1000,
    "chunk_overlap": 200,
}

DEFAULT_EMBEDDING_CONFIG = {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "model_type": EmbeddingModel.SENTENCE_TRANSFORMERS,
    "dimensions": 384,
}

DEFAULT_INDEX_CONFIG = {
    "name": "default-index",
    "index_type": IndexType.FAISS,
    "dimensions": 384,
    "similarity_metric": "cosine",
}

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
MAX_DOCUMENT_SIZE_MB = 50
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": [".pdf"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".txt"],
    "text/markdown": [".md"],
    "text/csv": [".csv"],
    "application/json": [".json"],
    "application/vnd.ms-excel": [".xls"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    "application/epub+zip": [".epub"],
}

# Chunking constants
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

# LLM constants
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024

# Vector store constants
DEFAULT_TOP_K = 5
SIMILARITY_THRESHOLD = 0.7 