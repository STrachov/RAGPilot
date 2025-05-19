from datetime import datetime, timezone, timedelta
import uuid
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey

from app.core.config.settings import settings

if TYPE_CHECKING:
    from app.core.models.user import User


class RefreshToken(SQLModel, table=True):
    """Refresh token for extending user sessions"""
    
    __tablename__ = "refresh_tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(sa_column=Column(String(255), unique=True, index=True))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE")))
    expires_at: datetime = Field(sa_column=Column(DateTime))
    revoked: bool = Field(default=False, sa_column=Column(Boolean))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    
    # SQLModel relationship
    user: Optional["User"] = Relationship(back_populates="refresh_tokens")
    
    @classmethod
    def create_for_user(cls, user_id: str) -> "RefreshToken":
        """Create a new refresh token for a user"""
        return RefreshToken(
            token=str(uuid.uuid4()),
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if the refresh token is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the refresh token is valid"""
        return not self.revoked and not self.is_expired


class TokenResponse(SQLModel):
    """Response schema for refresh token operations"""
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    expires_at: datetime
