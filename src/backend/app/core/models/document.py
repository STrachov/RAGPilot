from datetime import datetime
from typing import Optional, List, TYPE_CHECKING, Dict, Any
import json
import uuid

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from pydantic import BaseModel, field_validator

from app.core.config.constants import DocumentSourceType, DocumentStatus, ProcessingStage, StageStatus
from app.core.config.processing_config import ParseConfig, DEFAULT_PARSE_CONFIG

# Forward reference for circular imports
if TYPE_CHECKING:
    from app.core.models.monitoring import RetrievalResult
    RetrievalResult_type = RetrievalResult
else:
    RetrievalResult_type = "RetrievalResult"


# Pydantic models for API responses
class DocumentStageInfo(BaseModel):
    """Stage information within document status"""
    #model_config = {"extra": "allow"}  # Allow extra fields to pass through
    
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    error_message: Optional[str] = None
    attempts: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None  # For storing RAGParser response
    
    # Additional fields found in actual database status
    parser_used: Optional[str] = None
    ragparser_task_id: Optional[str] = None
    queue_position: Optional[int] = None
    pages_processed: Optional[int] = None
    file_size: Optional[int] = None  # For upload stage


class DocumentStatusStructure(BaseModel):
    """Simplified document status structure"""
    stages: Dict[str, DocumentStageInfo]


class DocumentResponse(BaseModel):
    """Document response model that automatically parses JSON status"""
    id: str
    filename: str
    title: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    file_path: Optional[str] = None  # Can be None during upload stage
    content_type: str
    file_size: int
    status: DocumentStatusStructure
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator('status', mode='before')
    @classmethod
    def parse_status_json(cls, v):
        """Parse status from JSON string to object"""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed
            except json.JSONDecodeError:
                # Return default structure for invalid JSON
                return {
                    "stages": {
                        "upload": {"status": "completed"},
                        "parse": {"status": "waiting"},
                        "chunk-index": {"status": "waiting"}
                    }
                }
        return v

    @classmethod
    def from_document(cls, document: "Document") -> "DocumentResponse":
        """Create DocumentResponse from Document model"""
        return cls(
            id=document.id,
            filename=document.filename,
            title=document.title,
            source_type=document.source_type,
            source_name=document.source_name,
            file_path=document.file_path,
            content_type=document.content_type,
            file_size=document.file_size,
            status=document.status,  # Will be parsed by field_validator
            metadata=document.metadata_dict,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


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
    file_path: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))  # Nullable for async upload
    content_type: str = Field(sa_column=Column(String(100)))
    file_size: int = Field(sa_column=Column(Integer))
    
    # New optimized fields
    binary_hash: Optional[str] = Field(default=None, sa_column=Column(String(64), nullable=True, index=True))
    
    # JSON fields for complex data
    status: str = Field(default="", sa_column=Column(Text))
    metadata_json: Optional[str] = Field(default=None, sa_column=Column("metadata", Text, nullable=True))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    
    # Relationship
    chunks: List["DocumentChunk"] = Relationship(back_populates="document")
    
    @property
    def parse_config(self) -> ParseConfig:
        """Get parse configuration from status.stages.parse.config"""
        stages = self.stages
        parse_stage = stages.get("parse", {})
        config_data = parse_stage.get("config", {})
        
        if not config_data:
            return DEFAULT_PARSE_CONFIG
        
        try:
            return ParseConfig(**config_data)
        except (TypeError, ValueError):
            return DEFAULT_PARSE_CONFIG
    
    @parse_config.setter
    def parse_config(self, value: ParseConfig):
        """Set parse configuration in status.stages.parse.config"""
        status_dict = self.status_dict
        
        # Ensure stages structure exists
        if "stages" not in status_dict:
            status_dict["stages"] = {}
        if "parse" not in status_dict["stages"]:
            status_dict["stages"]["parse"] = {}
            
        # Set the config
        status_dict["stages"]["parse"]["config"] = value.dict()
        self.status_dict = status_dict
    
    @property
    def ragparser_task_id(self) -> Optional[str]:
        """Get RAGParser task ID from status.stages.parse.ragparser_task_id"""
        stages = self.stages
        parse_stage = stages.get("parse", {})
        return parse_stage.get("ragparser_task_id")
    
    @ragparser_task_id.setter
    def ragparser_task_id(self, value: Optional[str]):
        """Set RAGParser task ID in status.stages.parse.ragparser_task_id"""
        status_dict = self.status_dict
        
        # Ensure stages structure exists
        if "stages" not in status_dict:
            status_dict["stages"] = {}
        if "parse" not in status_dict["stages"]:
            status_dict["stages"]["parse"] = {}
            
        # Set the task ID
        if value is not None:
            status_dict["stages"]["parse"]["ragparser_task_id"] = value
        else:
            status_dict["stages"]["parse"].pop("ragparser_task_id", None)
            
        self.status_dict = status_dict
    
    @property
    def metadata_dict(self) -> Optional[Dict[str, Any]]:
        """Get metadata as a dictionary (static document characteristics only)"""
        if self.metadata_json is None:
            return None
        return json.loads(self.metadata_json)
    
    @metadata_dict.setter
    def metadata_dict(self, value: Optional[Dict[str, Any]]):
        """Set metadata from a dictionary (static document characteristics only)"""
        if value is None:
            self.metadata_json = None
        else:
            self.metadata_json = json.dumps(value)
    
    @property
    def status_dict(self) -> Dict[str, Any]:
        """Get status as a dictionary with processing stages structure"""
        if not self.status:
            # Return default structure if status is empty
            return self._get_default_status_structure()
        
        try:
            return json.loads(self.status)
        except (json.JSONDecodeError, TypeError):
            # If status contains old simple string, convert it
            return self._get_default_status_structure()
    
    @status_dict.setter
    def status_dict(self, value: Dict[str, Any]):
        """Set status from a dictionary"""
        self.status = json.dumps(value)
    
    def _get_default_status_structure(self) -> Dict[str, Any]:
        """Get the default status structure with simplified format"""
        return {
            "stages": {
                "upload": {
                    "status": "completed",
                    "started_at": self.created_at.isoformat() if self.created_at else datetime.utcnow().isoformat(),
                    "completed_at": self.created_at.isoformat() if self.created_at else datetime.utcnow().isoformat(),
                    "attempts": 1
                },
                "parse": {
                    "status": "waiting",
                    "config": {
                        "do_ocr": True,
                        "extract_tables": True,
                        "extract_images": False,
                        "ocr_language": "en"
                    }
                },
                "chunk": {
                    "status": "waiting",
                    "config": {
                        "strategy": "recursive",
                        "chunk_size": 1000,
                        "chunk_overlap": 200
                    }
                },
                "index": {
                    "status": "waiting",
                    "config": {
                        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                        "model_type": "sentence-transformers",
                        "dimensions": 384,
                        "index_type": "faiss",
                        "similarity_metric": "cosine"
                    }
                }
            }
        }
    
    @property
    def current_stage(self) -> str:
        """Get the current active stage (derived from stages)"""
        stages = self.stages
        stage_order = ["upload", "parse", "chunk", "index"]
        
        # Find the first non-completed stage
        for stage_name in stage_order:
            stage = stages.get(stage_name, {})
            if stage.get("status") != "completed":
                return stage_name
        
        # If all stages are completed, return the last stage
        return stage_order[-1]
    
    @property
    def stage_status(self) -> str:
        """Get the current stage status (derived from current stage)"""
        current_stage = self.current_stage
        stages = self.stages
        return stages.get(current_stage, {}).get("status", "waiting")
    
    @property
    def stages(self) -> Dict[str, Dict[str, Any]]:
        """Get all processing stages"""
        return self.status_dict.get("stages", {})
    
    def update_current_stage(self, stage: str, status: str):
        """Update current stage and its status (simplified)"""
        status_data = self.status_dict
        
        # Just update the specific stage status - current_stage is derived
        if "stages" not in status_data:
            status_data["stages"] = {}
        if stage not in status_data["stages"]:
            status_data["stages"][stage] = {}
            
        status_data["stages"][stage]["status"] = status
        self.status_dict = status_data
    
    def update_stage_status(self, stage: str, status: str, **kwargs):
        """Update a specific stage status with additional data"""
        status_data = self.status_dict
        
        if "stages" not in status_data:
            status_data["stages"] = {}
        
        if stage not in status_data["stages"]:
            status_data["stages"][stage] = {}
            
        status_data["stages"][stage]["status"] = status
        
        # Add any additional data
        for key, value in kwargs.items():
            status_data["stages"][stage][key] = value
            
        self.status_dict = status_data
    
    @property
    def document_source_type(self) -> Optional[DocumentSourceType]:
        """Get the enum value for source_type"""
        if self.source_type is None:
            return None
        return DocumentSourceType(self.source_type)
    
    # Backward compatibility properties (can be removed later)
    @property
    def processing_stages(self) -> Dict[str, Dict[str, Any]]:
        """Backward compatibility - get stages from new status structure"""
        return self.stages
    
    @property
    def overall_status(self) -> str:
        """Get overall document status"""
        stages = self.stages
        
        # Check if any stage failed
        for stage in stages.values():
            if stage.get("status") == "failed":
                return "failed"
        
        # Check if any stage is running
        for stage in stages.values():
            if stage.get("status") == "running":
                return "processing"
        
        # Check if all stages are completed
        upload_done = stages.get("upload", {}).get("status") == "completed"
        parse_done = stages.get("parse", {}).get("status") == "completed"
        chunk_done = stages.get("chunk", {}).get("status") == "completed"
        index_done = stages.get("index", {}).get("status") == "completed"
        
        if upload_done and parse_done and chunk_done and index_done:
            return "completed"
        
        # Otherwise, document is pending processing
        return "pending"


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