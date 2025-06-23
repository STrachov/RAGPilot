from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session

from app.api.deps import SessionDep, get_current_user
from app.core.models.user import User
from app.core.config.processing_config import GlobalProcessingConfig, ChunkConfig, IndexConfig
from app.core.services.config_service import config_service
from app.core.services.bulk_processor import bulk_processor

router = APIRouter(prefix="/config", tags=["configuration"])

async def get_current_user_dep(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to get current user"""
    return current_user

@router.get("/global", response_model=Dict[str, Any])
async def get_global_config(
    current_user: User = Depends(get_current_user_dep)
) -> Dict[str, Any]:
    """
    Get the current global processing configuration
    
    Returns:
        Dict containing global chunk and index configuration
    """
    try:
        global_config = config_service.get_global_config()
        return {
            "chunk_config": global_config.chunk_config.dict(),
            "index_config": global_config.index_config.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get global configuration: {str(e)}")

@router.put("/global")
async def update_global_config(
    config_data: Dict[str, Any],
    session: SessionDep,
    current_user: User = Depends(get_current_user_dep)
) -> Dict[str, str]:
    """Update global processing configuration"""
    try:
        # Parse the configuration
        global_config = GlobalProcessingConfig.from_dict(config_data)
        
        # Update the configuration
        success = config_service.update_global_config(global_config)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update global configuration")
        
        return {"message": "Global configuration updated successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")

@router.get("/chunk", response_model=Dict[str, Any])
async def get_chunk_config(
    current_user: User = Depends(get_current_user_dep)
) -> Dict[str, Any]:
    """Get current chunk configuration"""
    try:
        return config_service.get_chunk_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunk configuration: {str(e)}")

@router.get("/index", response_model=Dict[str, Any])
async def get_index_config(
    current_user: User = Depends(get_current_user_dep)
) -> Dict[str, Any]:
    """Get current index configuration"""
    try:
        return config_service.get_index_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get index configuration: {str(e)}")

@router.post("/apply-to-all")
async def apply_global_config_to_all(
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: User = Depends(get_current_user_dep)
) -> Dict[str, str]:
    """Apply current global configuration to all documents"""
    try:
        # Start bulk processing in background
        background_tasks.add_task(
            bulk_processor.apply_global_config_to_all_documents
        )
        
        return {
            "message": "Bulk reprocessing started. All documents will be reprocessed with current global configuration."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bulk processing: {str(e)}")

@router.post("/invalidate-cache")
async def invalidate_config_cache(
    current_user: User = Depends(get_current_user_dep)
) -> Dict[str, str]:
    """Invalidate the configuration cache (admin only)"""
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        config_service.invalidate_cache()
        return {"message": "Configuration cache invalidated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate cache: {str(e)}")

@router.get("/bulk-status")
async def get_bulk_processing_status(
    current_user: User = Depends(get_current_user_dep)
) -> Dict[str, Any]:
    """Get status of bulk processing operations"""
    try:
        status = bulk_processor.get_processing_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bulk processing status: {str(e)}") 