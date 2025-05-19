import logging
import os
import sys
from datetime import datetime
from functools import lru_cache
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.core.config.settings import settings


class LogConfig(BaseModel):
    """Logging configuration"""
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s | %(levelname)s | %(message)s | [%(name)s:%(lineno)d]"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    LOG_DIR: str = "logs"
    LOG_FILE_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_TO_CONSOLE: bool = True
    LOG_TO_FILE: bool = True


@lru_cache
def get_log_config() -> LogConfig:
    """Get logging configuration from environment or defaults"""
    return LogConfig()


def get_logger(name: str, config: Optional[LogConfig] = None) -> logging.Logger:
    """
    Get a configured logger instance for the specified module.
    
    Args:
        name: The name of the logger (typically __name__ from the calling module)
        config: Optional custom log configuration
        
    Returns:
        A configured logger instance
    """
    if config is None:
        config = get_log_config()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Clear any existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    log_formatter = logging.Formatter(
        fmt=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    
    # Add console handler if enabled
    if config.LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if enabled
    if config.LOG_TO_FILE:
        log_dir = Path(os.path.join(os.path.dirname(__file__), "..", "..", config.LOG_DIR))
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{datetime.now().strftime('%Y%m%d')}_app.log"
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=config.LOG_FILE_MAX_BYTES,
            backupCount=config.LOG_FILE_BACKUP_COUNT
        )
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_request_response(request_data: Dict[str, Any], 
                         response_data: Dict[str, Any], 
                         endpoint: str,
                         logger: logging.Logger) -> None:
    """
    Log API request and response data for monitoring.
    
    Args:
        request_data: The incoming request data
        response_data: The outgoing response data
        endpoint: The endpoint being called
        logger: The logger instance to use
    """
    # Skip logging sensitive auth endpoints or large responses
    if "auth" in endpoint or "login" in endpoint:
        request_data = {"message": "[REDACTED FOR SECURITY]"}
    
    log_data = {
        "endpoint": endpoint,
        "request": request_data,
        "response_status": response_data.get("status", "unknown"),
    }
    
    logger.info(f"API call: {log_data}")


# Create application loggers
app_logger = get_logger("app")
api_logger = get_logger("api")
db_logger = get_logger("db")
auth_logger = get_logger("auth")
document_logger = get_logger("document")
chat_logger = get_logger("chat")

# Disable noisy loggers
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING) 