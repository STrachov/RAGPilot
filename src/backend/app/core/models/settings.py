from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field


class SettingType(str, Enum):
    """Types of system settings"""
    API_KEY = "api_key"
    CONNECTION = "connection"
    FEATURE_FLAG = "feature_flag"
    SYSTEM_CONFIG = "system_config"
    ENVIRONMENT = "environment"


class Setting(SQLModel):
    """Model for system settings"""
    id: Optional[str] = None
    key: str
    value: Any
    type: SettingType
    description: Optional[str] = None
    is_secret: bool = False
    is_editable: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Environment(SQLModel):
    """Model for environment configuration"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    is_production: bool = False
    variables: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None 