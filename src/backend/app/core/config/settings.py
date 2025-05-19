from pydantic_settings import BaseSettings
from typing import List, Optional, Set, Dict, ClassVar, Union, Literal
from pydantic import field_validator, ConfigDict
import os
import json


# Database naming convention
DB_NAMING_CONVENTION: Dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # Allow extra fields from environment variables
    )

    # API related settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "RAGPilot"
    DOMAIN: str = "localhost"
    FRONTEND_HOST: str = "http://localhost:3000"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    STACK_NAME: str = "full-stack-ai-project"
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-development-only")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS settings
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["*"]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database settings
    POSTGRES_SERVER: str
    POSTGRES_PORT: int 
    POSTGRES_USER: str 
    POSTGRES_PASSWORD: str 
    POSTGRES_DB: str 
    
    # Database URI - calculated on init
    SQLALCHEMY_DATABASE_URI: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate the database URI during initialization
        self.SQLALCHEMY_DATABASE_URI = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # User settings
    FIRST_SUPERUSER: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin"
    
    # Email settings
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # S3 storage settings
    S3_BUCKET_NAME: str 
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_REGION: str
    S3_ENDPOINT_URL: Optional[str] 
    
    # File upload settings
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "100000000"))  # 100MB
    ALLOWED_DOCUMENT_TYPES: Set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
    }
    FILE_UPLOAD_TIMEOUT: int = int(os.getenv("FILE_UPLOAD_TIMEOUT", "300"))  # 5 minutes
    
    # Task queue settings
    USE_REDIS: bool = os.getenv("USE_REDIS", "False").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Docker settings
    DOCKER_IMAGE_BACKEND: str = "backend"
    DOCKER_IMAGE_FRONTEND: str = "frontend"
    
    # Langfuse settings
    LANGFUSE_SECRET: Optional[str] = None
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    
    # CORS origins getter
    @property
    def all_cors_origins(self) -> List[str]:
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [self.BACKEND_CORS_ORIGINS]
        return self.BACKEND_CORS_ORIGINS


settings = Settings() 