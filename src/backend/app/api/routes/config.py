"""
Configuration management routes
Handles global processing configuration using file-based storage
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from app.core.config.constants import GlobalProcessingConfig, ChunkConfig, IndexConfig, ParseConfig
from app.core.services.config_service import config_service
from app.api.deps import get_current_admin
from app.core.models.user import User

router = APIRouter()

@router.get("/global", response_model=Dict[str, Any])
async def get_global_config(
    current_user: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Get the current global processing configuration
    
    Returns:
        Dict containing global parse, chunk and index configuration
    """
    try:
        global_config = config_service.get_global_config()
        return {
            "parse_config": global_config.parse_config.model_dump(),
            "chunk_config": global_config.chunk_config.model_dump(),
            "index_config": global_config.index_config.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get global configuration: {str(e)}")

@router.put("/global", response_model=Dict[str, str])
async def update_global_config(
    config: GlobalProcessingConfig,
    current_user: User = Depends(get_current_admin)
) -> Dict[str, str]:
    """
    Update the global processing configuration
    
    Args:
        config: New global configuration
        
    Returns:
        Success message
    """
    try:
        config_service.update_global_config(config)
        return {"message": "Global configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update global configuration: {str(e)}")

@router.get("/parse", response_model=Dict[str, Any])
async def get_parse_config(
    current_user: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """Get current parse configuration"""
    try:
        return config_service.get_parse_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get parse configuration: {str(e)}")

@router.get("/chunk", response_model=Dict[str, Any])
async def get_chunk_config(
    current_user: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """Get current chunk configuration"""
    try:
        return config_service.get_chunk_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunk configuration: {str(e)}")

@router.get("/index", response_model=Dict[str, Any])
async def get_index_config(
    current_user: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """Get current index configuration"""
    try:
        return config_service.get_index_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get index configuration: {str(e)}")

@router.post("/invalidate-cache", response_model=Dict[str, str])
async def invalidate_cache(
    current_user: User = Depends(get_current_admin)
) -> Dict[str, str]:
    """
    Invalidate configuration cache (admin only)
    Forces reload from file on next access
    """
    try:
        config_service.invalidate_cache()
        return {"message": "Configuration cache invalidated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate cache: {str(e)}")

@router.post("/reload", response_model=Dict[str, str])
async def reload_config(
    current_user: User = Depends(get_current_admin)
) -> Dict[str, str]:
    """
    Force reload configuration from file
    """
    try:
        config_service.reload_config()
        return {"message": "Configuration reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload configuration: {str(e)}")

@router.post("/backup", response_model=Dict[str, str])
async def backup_config(
    current_user: User = Depends(get_current_admin)
) -> Dict[str, str]:
    """
    Create a backup of current configuration
    """
    try:
        backup_path = config_service.backup_config()
        return {"message": f"Configuration backed up to {backup_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to backup configuration: {str(e)}")

@router.get("/status", response_model=Dict[str, Any])
async def get_config_status(
    current_user: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Get configuration system status
    """
    try:
        import os
        config_file_path = config_service.config_file
        
        status = {
            "config_file_exists": config_file_path.exists(),
            "config_file_path": str(config_file_path),
            "config_file_size": os.path.getsize(config_file_path) if config_file_path.exists() else 0,
            "cache_status": "loaded" if config_service._config_cache is not None else "empty"
        }
        
        if config_file_path.exists():
            stat = os.stat(config_file_path)
            status["last_modified"] = stat.st_mtime
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration status: {str(e)}") 