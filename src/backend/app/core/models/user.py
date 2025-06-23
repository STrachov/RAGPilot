#from __future__ import annotations  # Enables forward references in type hints

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING, Set

from pydantic import EmailStr, ConfigDict, Field as PydanticField
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
import json

from app.core.config.constants import UserRole, ROLE_PERMISSIONS

# Forward references for circular imports
if TYPE_CHECKING:
    from app.core.models.monitoring import Query, Feedback
    from app.core.models.refresh_token import RefreshToken
    Query_type = Query
    Feedback_type = Feedback
    RefreshToken_type = RefreshToken
else:
    Query_type = "Query"
    Feedback_type = "Feedback"
    RefreshToken_type = "RefreshToken"


# Shared properties for Pydantic models
class UserBase(SQLModel):
    email: EmailStr
    is_active: bool = True
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str


# Properties to receive via API on update
class UserUpdate(SQLModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    preferences: Optional[Dict[str, Any]] = None


class UserRegister(SQLModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserUpdateMe(SQLModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    preferences: Optional[Dict[str, Any]] = None


class UpdatePassword(SQLModel):
    current_password: str
    new_password: str


# Database table model using SQLModel
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    # Auto-incrementing integer primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Public ID as UUID string
    user_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), unique=True, index=True)
    )
    
    # Basic user fields
    email: str = Field(sa_column=Column(String(255), unique=True, index=True))
    hashed_password: str = Field(sa_column=Column(String(255)))
    full_name: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(Boolean))
    role: str = Field(default=UserRole.USER.value, sa_column=Column(String(50)))
    
    # Additional fields
    preferences_json: Optional[str] = Field(default=None, sa_column=Column("preferences", Text, nullable=True))
    
    # Timestamps
    last_login: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    
    # Relationships
    refresh_tokens: List[RefreshToken_type] = Relationship(back_populates="user")
    
    @property
    def preferences(self) -> Optional[Dict[str, Any]]:
        """Get metadata as a dictionary"""
        if self.preferences_json is None:
            return None
        return json.loads(self.preferences_json)
    
    @preferences.setter
    def preferences(self, value: Optional[Dict[str, Any]]):
        """Set metadata from a dictionary"""
        if value is None:
            self.preferences_json = None
        else:
            self.preferences_json = json.dumps(value)
    
    @property
    def user_role(self) -> UserRole:
        """Get the enum value for the role"""
        return UserRole(self.role)
    
    @property
    def is_superuser(self) -> bool:
        """Legacy property for compatibility"""
        return self.user_role == UserRole.ADMIN
    
    @property
    def permissions(self) -> Set[str]:
        """Get all permissions for this user based on role"""
        return ROLE_PERMISSIONS.get(self.user_role, set())
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions


# Properties to return via API
class UserPublic(SQLModel):
    id: str  # Using the UUID string as the public ID
    email: str
    is_active: bool
    full_name: Optional[str] = None
    role: str
    preferences: Optional[Dict[str, Any]] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[str] = []


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    message: Optional[str] = None
    role: str = UserRole.USER.value
    permissions: List[str] = []


# Request model for refresh token
class RefreshTokenRequest(SQLModel):
    refresh_token: str


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None


class NewPassword(SQLModel):
    token: str
    new_password: str

