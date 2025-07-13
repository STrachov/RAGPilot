"""
Stage Registry Service
Manages registration and execution of pipeline stages
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
from sqlmodel import Session

from app.core.models.document import Document
from app.core.models.pipeline import PipelineStage, StageResult, StageStatus
from app.core.logger import app_logger as logger
import uuid
from app.core.config.pipelines import predefined_pipelines

class StageFunction:
    """Wrapper for stage execution functions"""
    
    def __init__(
        self, 
        func: Callable, 
        dependencies: List[str] = None,
        description: str = "",
        timeout_seconds: Optional[int] = None
    ):
        self.func = func
        self.dependencies = dependencies or []
        self.description = description
        self.timeout_seconds = timeout_seconds
        self.name = func.__name__


class StageRegistry:
    """Registry for managing all available pipeline stages"""
    
    def __init__(self):
        self._stages: Dict[str, StageFunction] = {}
        self._initialized = False
    
    def register_stage(
        self, 
        name: str, 
        func: Callable,
        dependencies: List[str] = None,
        description: str = "",
        timeout_seconds: Optional[int] = None
    ) -> None:
        """Register a stage function"""
        if name in self._stages:
            logger.warning(f"Stage '{name}' is already registered, overwriting")
        
        self._stages[name] = StageFunction(
            func=func,
            dependencies=dependencies or [],
            description=description,
            timeout_seconds=timeout_seconds
        )
        logger.debug(f"Registered stage: {name}")
    
    def get_stage(self, name: str) -> Optional[StageFunction]:
        """Get a registered stage function"""
        return self._stages.get(name)
    
    def list_stages(self) -> List[str]:
        """Get list of all registered stage names"""
        return list(self._stages.keys())
    
    def is_registered(self, name: str) -> bool:
        """Check if a stage is registered"""
        return name in self._stages
    
    async def execute_stage(
        self,
        stage: PipelineStage,
        document: Document,
        session: Session,
        context: Dict[str, Any] = None
    ) -> StageResult:
        """Execute a registered stage with error handling and timing"""
        start_time = datetime.now(timezone.utc)
        context = context or {}
        previous_stage_name = stage.dependencies[0] if stage.dependencies else None
        previous_stage = document.status_dict.get("stages", {}).get(previous_stage_name, None)

        generic_kwargs: Dict[str, Any] = {
            "pipeline_name": context.get("pipeline_name"),
            "stage_name": stage.name,
            "started_at": start_time.isoformat(),
            "config": stage.config,
            "execution_id": context.get("execution_id"),
            "stage_id": str(uuid.uuid4()),
            "previous_stage_id": previous_stage.stage_id,
        }
        try:
            logger.info(f"Executing stage '{stage.name}' for document {document.id}")
            
            # Check if stage is registered
            stage_func = self.get_stage(stage.function_name)
            if not stage_func:
                raise ValueError(f"Stage function '{stage.function_name}' is not registered")
            
            # Prepare execution context
            execution_config = {**stage.config}
            if context:
                execution_config["context"] = context
                execution_config["previous_results"] = context.get("previous_results", {})
            
            # Execute stage with timeout if specified
            timeout = stage.timeout_seconds or stage_func.timeout_seconds
            logger.info(f"Stage '{stage.name}' starting ...")
            if timeout:
                result = await asyncio.wait_for(
                    stage_func.func(document, session, execution_config),
                    timeout=timeout
                )
            else:
                result = await stage_func.func(document, session, execution_config)
                
            result_kwargs = result.model_dump()
            logger.info(f"Stage '{stage.name}' started successfully with result: {str(result_kwargs)}")
            return StageResult(
                **generic_kwargs,
                **result_kwargs
            )
            
            
        except asyncio.TimeoutError:
            error_msg = f"Stage '{stage.name}' timed out after {timeout} seconds"
            logger.error(error_msg)
            return StageResult(
                **generic_kwargs,
                status=StageStatus.FAILED,
                error_message=error_msg,
            )
            
        except Exception as e:
            error_msg = f"Stage '{stage.name}' failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return StageResult(
                **generic_kwargs,
                status=StageStatus.FAILED,
                error_message=error_msg,
            )

    
    def validate_dependencies(self, stages: List[PipelineStage]) -> List[str]:
        """Validate that all stage dependencies are registered"""
        errors = []
        
        for stage in stages:
            if not self.is_registered(stage.function_name):
                errors.append(f"Stage function '{stage.function_name}' is not registered")
                
            # Check if dependencies exist in the stage list
            stage_names = {s.name for s in stages}
            for dep in stage.dependencies:
                if dep not in stage_names:
                    errors.append(f"Stage '{stage.name}' depends on '{dep}' which is not in the pipeline")
        
        return errors
    
    def get_stage_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered stages"""
        return {
            name: {
                "description": stage_func.description,
                "dependencies": stage_func.dependencies,
                "timeout_seconds": stage_func.timeout_seconds,
                "function_name": stage_func.name
            }
            for name, stage_func in self._stages.items()
        }


# Global registry instance
stage_registry = StageRegistry() 