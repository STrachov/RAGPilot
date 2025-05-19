from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"


class LLMConfig(SQLModel):
    """Configuration for LLM models"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    additional_params: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class PromptTemplate(SQLModel):
    """Model for prompt templates"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    template: str
    variables: List[str] = []
    system_message: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class PromptConfig(SQLModel):
    """Configuration linking LLM models with prompt templates"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    llm_config_id: str
    prompt_template_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None 