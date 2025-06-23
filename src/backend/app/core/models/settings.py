from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import uuid
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Text, Boolean, DateTime


class SettingType(str, Enum):
    """Types of system settings"""
    API_KEY = "api_key"
    CONNECTION = "connection"
    FEATURE_FLAG = "feature_flag"
    SYSTEM_CONFIG = "system_config"
    ENVIRONMENT = "environment"


class Setting(SQLModel, table=True):
    """Model for system settings"""
    __tablename__ = "settings"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True)
    )
    key: str = Field(sa_column=Column(String(255), unique=True, index=True))
    value: str = Field(sa_column=Column(Text))  # Store as JSON string
    type: str = Field(sa_column=Column(String(50)))
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    is_secret: bool = Field(default=False, sa_column=Column(Boolean))
    is_editable: bool = Field(default=True, sa_column=Column(Boolean))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))


class Environment(SQLModel):
    """Model for environment configuration"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    is_production: bool = False
    variables: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None 