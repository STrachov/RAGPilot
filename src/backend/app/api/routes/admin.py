from typing import Any, Dict, List, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep, get_user_with_permission
from app.core.config.constants import (
    DEFAULT_CHUNKING_CONFIG,
    DEFAULT_EMBEDDING_CONFIG,
    DEFAULT_INDEX_CONFIG,
    DEFAULT_RETRIEVAL_STRATEGY,
    DEFAULT_LLM_CONFIG,
    DEFAULT_PROMPT_TEMPLATES,
    ChunkingStrategy,
    EmbeddingModel,
    IndexType,
    RetrievalMethod,
    LLMProvider
)

router = APIRouter()

# Admin-only dependency
def require_admin_permission(current_user: CurrentUser) -> CurrentUser:
    if not current_user.has_permission("config:read"):
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions to access this resource"
        )
    return current_user

def require_admin_write_permission(current_user: CurrentUser) -> CurrentUser:
    if not current_user.has_permission("config:write"):
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions to modify this resource"
        )
    return current_user

# Create annotated types for the dependencies
AdminUser = Annotated[CurrentUser, Depends(require_admin_permission)]
AdminWriteUser = Annotated[CurrentUser, Depends(require_admin_write_permission)]


class SystemStats(BaseModel):
    """System statistics"""
    total_documents: int
    total_chunks: int
    total_queries: int
    active_users: int
    storage_used_mb: float


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: AdminUser,
) -> Any:
    """Get system statistics for admin dashboard"""
    # In a real implementation, you would query the database for these statistics
    # For now, we'll return dummy data
    return SystemStats(
        total_documents=42,
        total_chunks=1024,
        total_queries=156,
        active_users=7,
        storage_used_mb=125.4
    )


@router.get("/config/chunking")
async def get_chunking_config(
    current_user: AdminUser,
) -> Any:
    """Get chunking configuration"""
    return DEFAULT_CHUNKING_CONFIG


@router.get("/config/embedding")
async def get_embedding_config(
    current_user: AdminUser,
) -> Any:
    """Get embedding configuration"""
    return DEFAULT_EMBEDDING_CONFIG


@router.get("/config/index")
async def get_index_config(
    current_user: AdminUser,
) -> Any:
    """Get index configuration"""
    return DEFAULT_INDEX_CONFIG


@router.get("/config/retrieval")
async def get_retrieval_config(
    current_user: AdminUser,
) -> Any:
    """Get retrieval configuration"""
    return DEFAULT_RETRIEVAL_STRATEGY


@router.get("/config/llm")
async def get_llm_config(
    current_user: AdminUser,
) -> Any:
    """Get LLM configuration"""
    return DEFAULT_LLM_CONFIG


@router.get("/config/prompts")
async def get_prompt_templates(
    current_user: AdminUser,
) -> Any:
    """Get prompt templates"""
    return DEFAULT_PROMPT_TEMPLATES


class ChunkingConfigUpdate(BaseModel):
    """Chunking configuration update"""
    strategy: ChunkingStrategy
    chunk_size: int
    chunk_overlap: int
    separators: Optional[List[str]] = None


@router.post("/config/chunking")
async def update_chunking_config(
    config: ChunkingConfigUpdate,
    current_user: AdminWriteUser,
) -> Any:
    """Update chunking configuration"""
    # In a real implementation, you would save this to a database or config file
    # For now, we'll just return it
    return {
        "message": "Chunking configuration updated successfully",
        "config": config
    }


class EmbeddingConfigUpdate(BaseModel):
    """Embedding configuration update"""
    model_name: str
    model_type: EmbeddingModel
    dimensions: int
    api_key: Optional[str] = None
    
    model_config = {"protected_namespaces": ()}


@router.post("/config/embedding")
async def update_embedding_config(
    config: EmbeddingConfigUpdate,
    current_user: AdminWriteUser,
) -> Any:
    """Update embedding configuration"""
    return {
        "message": "Embedding configuration updated successfully",
        "config": config
    }


class IndexConfigUpdate(BaseModel):
    """Index configuration update"""
    name: str
    index_type: IndexType
    dimensions: int
    similarity_metric: str = "cosine"
    connection_params: Optional[Dict[str, Any]] = None


@router.post("/config/index")
async def update_index_config(
    config: IndexConfigUpdate,
    current_user: AdminWriteUser,
) -> Any:
    """Update index configuration"""
    return {
        "message": "Index configuration updated successfully",
        "config": config
    }


class RetrievalStrategyUpdate(BaseModel):
    """Retrieval strategy update"""
    method: RetrievalMethod
    top_k: int
    score_threshold: Optional[float] = None
    semantic_weight: Optional[float] = None
    keyword_weight: Optional[float] = None


@router.post("/config/retrieval")
async def update_retrieval_strategy(
    config: RetrievalStrategyUpdate,
    current_user: AdminWriteUser,
) -> Any:
    """Update retrieval strategy"""
    return {
        "message": "Retrieval strategy updated successfully",
        "config": config
    }


class LLMConfigUpdate(BaseModel):
    """LLM configuration update"""
    name: str
    provider: LLMProvider
    model_name: str
    max_tokens: int
    temperature: float
    api_key: Optional[str] = None
    
    model_config = {"protected_namespaces": ()}


@router.post("/config/llm")
async def update_llm_config(
    config: LLMConfigUpdate,
    current_user: AdminWriteUser,
) -> Any:
    """Update LLM configuration"""
    return {
        "message": "LLM configuration updated successfully",
        "config": config
    }


class PromptTemplateUpdate(BaseModel):
    """Prompt template update"""
    qa: str
    summarize: str


@router.post("/config/prompts")
async def update_prompt_templates(
    templates: PromptTemplateUpdate,
    current_user: AdminWriteUser,
) -> Any:
    """Update prompt templates"""
    return {
        "message": "Prompt templates updated successfully",
        "templates": templates
    } 