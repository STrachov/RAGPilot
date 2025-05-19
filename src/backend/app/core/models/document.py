from datetime import datetime
from typing import Optional, List, TYPE_CHECKING, Dict, Any
import json
import uuid

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey

# Import directly - this should work with the Python path set in main.py
from app.core.config.constants import DocumentSourceType, DocumentStatus

# Forward reference for circular imports
if TYPE_CHECKING:
    from app.core.models.monitoring import RetrievalResult
    RetrievalResult_type = RetrievalResult
else:
    RetrievalResult_type = "RetrievalResult"


class Document(SQLModel, table=True):
    """Model for uploaded documents"""
    __tablename__ = "documents"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True)
    )
    filename: str = Field(sa_column=Column(String(255)))
    title: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    source_type: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True))
    source_name: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    file_path: str = Field(sa_column=Column(String(255)))
    content_type: str = Field(sa_column=Column(String(100)))
    file_size: int = Field(sa_column=Column(Integer))
    status: str = Field(default=DocumentStatus.PENDING.value, sa_column=Column(String(50)))
    metadata_json: Optional[str] = Field(default=None, sa_column=Column("metadata", Text, nullable=True))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    processed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    
    # Relationship
    chunks: List["DocumentChunk"] = Relationship(back_populates="document")
    
    @property
    def metadata_dict(self) -> Optional[Dict[str, Any]]:
        """Get metadata as a dictionary"""
        if self.metadata_json is None:
            return None
        return json.loads(self.metadata_json)
    
    @metadata_dict.setter
    def metadata_dict(self, value: Optional[Dict[str, Any]]):
        """Set metadata from a dictionary"""
        if value is None:
            self.metadata_json = None
        else:
            self.metadata_json = json.dumps(value)
    
    @property
    def document_status(self) -> DocumentStatus:
        """Get the enum value for status"""
        return DocumentStatus(self.status)
    
    @property
    def document_source_type(self) -> Optional[DocumentSourceType]:
        """Get the enum value for source_type"""
        if self.source_type is None:
            return None
        return DocumentSourceType(self.source_type)


class DocumentChunk(SQLModel, table=True):
    """Model for document chunks after processing"""
    __tablename__ = "document_chunks"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True)
    )
    document_id: str = Field(
        sa_column=Column(
            String(36), 
            ForeignKey("documents.id", ondelete="CASCADE", onupdate="CASCADE")
        )
    )
    content: str = Field(sa_column=Column(Text))
    chunk_index: int = Field(sa_column=Column(Integer))
    metadata_json: Optional[str] = Field(default=None, sa_column=Column("metadata", Text, nullable=True))
    embedding_id: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    
    # Relationships
    document: Document = Relationship(back_populates="chunks")
    retrieval_results: List[RetrievalResult_type] = Relationship(back_populates="document_chunk")
    
    @property
    def metadata_dict(self) -> Optional[Dict[str, Any]]:
        """Get metadata as a dictionary"""
        if self.metadata_json is None:
            return None
        return json.loads(self.metadata_json)
    
    @metadata_dict.setter
    def metadata_dict(self, value: Optional[Dict[str, Any]]):
        """Set metadata from a dictionary"""
        if value is None:
            self.metadata_json = None
        else:
            self.metadata_json = json.dumps(value) 