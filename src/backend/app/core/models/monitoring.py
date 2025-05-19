from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import uuid

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON

# Direct import from constants
from app.core.config.constants import QueryStatus

# Forward references for circular imports
if TYPE_CHECKING:
    from app.core.models.user import User
    from app.core.models.document import DocumentChunk
    User_type = User
    DocumentChunk_type = DocumentChunk
else:
    User_type = "User"
    DocumentChunk_type = "DocumentChunk"


class Query(SQLModel, table=True):
    """Model for user queries"""
    __tablename__ = "queries"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True)
    )
    user_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String(36), 
            ForeignKey("users.user_id", ondelete="SET NULL", onupdate="CASCADE"), 
            nullable=True
        )
    )
    query_text: str = Field(sa_column=Column(String(1000)))
    session_id: Optional[str] = Field(default=None, sa_column=Column(String(100), nullable=True))
    status: str = Field(default=QueryStatus.PENDING.value, sa_column=Column(String(50)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    completed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    
    # Relationships
    user: Optional[User_type] = Relationship(sa_relationship_kwargs={
        "foreign_keys": "[Query.user_id]", 
        "primaryjoin": "Query.user_id == User.user_id"
    })
    retrieval_results: List["RetrievalResult"] = Relationship(back_populates="query")
    responses: List["Response"] = Relationship(back_populates="query")
    
    @property
    def query_status(self) -> QueryStatus:
        """Get the enum value for status"""
        return QueryStatus(self.status)


class RetrievalResult(SQLModel, table=True):
    """Model for retrieval results"""
    __tablename__ = "retrieval_results"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True)
    )
    query_id: str = Field(
        sa_column=Column(
            String(36), 
            ForeignKey("queries.id", ondelete="CASCADE", onupdate="CASCADE")
        )
    )
    document_chunk_id: str = Field(
        sa_column=Column(
            String(36), 
            ForeignKey("document_chunks.id", ondelete="CASCADE", onupdate="CASCADE")
        )
    )
    score: float = Field(sa_column=Column(Float))
    rank: int = Field(sa_column=Column(Integer))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    
    # Relationships
    query: Query = Relationship(back_populates="retrieval_results")
    document_chunk: DocumentChunk_type = Relationship(back_populates="retrieval_results")


class Response(SQLModel, table=True):
    """Model for system responses"""
    __tablename__ = "responses"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True)
    )
    query_id: str = Field(
        sa_column=Column(
            String(36), 
            ForeignKey("queries.id", ondelete="CASCADE", onupdate="CASCADE")
        )
    )
    response_text: str = Field(sa_column=Column(String(5000)))
    sources: List[str] = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    
    # Relationships
    query: Query = Relationship(back_populates="responses")
    feedback: List["Feedback"] = Relationship(back_populates="response")


class Feedback(SQLModel, table=True):
    """Model for user feedback"""
    __tablename__ = "feedback"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True)
    )
    query_id: str = Field(
        sa_column=Column(
            String(36), 
            ForeignKey("queries.id", ondelete="CASCADE", onupdate="CASCADE")
        )
    )
    response_id: str = Field(
        sa_column=Column(
            String(36), 
            ForeignKey("responses.id", ondelete="CASCADE", onupdate="CASCADE")
        )
    )
    user_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String(36), 
            ForeignKey("users.user_id", ondelete="SET NULL", onupdate="CASCADE"), 
            nullable=True
        )
    )
    rating: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    feedback_text: Optional[str] = Field(default=None, sa_column=Column(String(1000), nullable=True))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    
    # Relationships
    query: Query = Relationship()
    response: Response = Relationship(back_populates="feedback")
    user: Optional[User_type] = Relationship(sa_relationship_kwargs={
        "foreign_keys": "[Feedback.user_id]", 
        "primaryjoin": "Feedback.user_id == User.user_id"
    }) 