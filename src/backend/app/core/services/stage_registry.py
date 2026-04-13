"""
Stage Registry Service
Manages registration and execution of pipeline stages
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
from sqlmodel import Session
from app.core.models.document import Document
from app.core.models.pipeline import PipelineStage, PipelineStageResult, PipelineStageStatus

from app.core.logger import app_logger as logger
import uuid

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
    ) -> PipelineStageResult:
        """Execute a registered stage with error handling and timing"""
        start_time = datetime.now(timezone.utc)
        context = context or {}
        previous_stage_name = stage.dependencies[0] if stage.dependencies else None
        
        # Safely get previous stage ID, handling None case
        previous_stage_id = None
        if previous_stage_name:
            stages_dict = document.status_dict.get("stages", {})
            previous_stage_data = stages_dict.get(previous_stage_name)
            if previous_stage_data:
                previous_stage_id = previous_stage_data.get("stage_id")
        
        logger.info(f"Previous stage name: {previous_stage_name}")       

        stage_func = self.get_stage(stage.function_name)
        if not stage_func:
            raise ValueError(f"Stage function '{stage.function_name}' is not registered")
        
        # Get timeout configuration early
        timeout = stage.timeout_seconds or stage_func.timeout_seconds
        
        try:
            logger.info(f"Executing stage '{stage.name}' for document {document.id}")
            
            # Prepare execution context
            execution_config = {**stage.config}
            if context:
                execution_config["context"] = context
                execution_config["previous_results"] = context.get("previous_results", {})
            
            # Execute stage with timeout if specified
            logger.info(f"Stage '{stage.name}' starting ...")
            if timeout:
                results = await asyncio.wait_for(
                    stage_func.func(document, session, execution_config),
                    timeout=timeout
                )
            else:
                results = await stage_func.func(document, session, execution_config)
                
            if "status" in results and results["status"] == PipelineStageStatus.RUNNING.value:
                logger.info(f"Stage '{stage.name}' started successfully with result: {str(results)}")
            else:
                logger.error(f"Stage '{stage.name}' failed with result: {str(results)}")

            return PipelineStageResult(
                started_at=start_time.isoformat(),
                status=results["status"],
                finished_at=datetime.now(timezone.utc).isoformat(),
                result=results["result"],
                error_message=results["error_message"]
            )
            
        except asyncio.TimeoutError:
            error_msg = f"Stage '{stage.name}' timed out after {timeout} seconds"
            logger.error(error_msg)
            return PipelineStageResult(
                started_at=start_time.isoformat(),
                status=PipelineStageStatus.FAILED.value,
                finished_at=datetime.now(timezone.utc).isoformat(),
                error_message=error_msg,
                result=None
            )
            
        except Exception as e:
            error_msg = f"Stage '{stage.name}' failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return PipelineStageResult(
                started_at=start_time.isoformat(),
                status=PipelineStageStatus.FAILED.value,
                finished_at=datetime.now(timezone.utc).isoformat(),
                error_message=error_msg,
                result=None
            )

    # async def _update_document_stage_status(
    #     self,
    #     document: Document,
    #     session: Session,
    #     stage_name: str,
    #     status: Optional[str] = None,
    #     execution_id: Optional[str] = None,
    #     result_data: Optional[Dict[str, Any]] = None
    # ) -> None:
    #     """Update the document's stage status"""
    #     try:
    #         status_dict = document.status_dict
    #         stages = status_dict.get("stages", {})
            
    #         if stage_name not in stages:
    #             stages[stage_name] = {}
            
    #         stages[stage_name]["status"] = status
    #         if status == "running":
    #             stages[stage_name]["started_at"] = datetime.now(timezone.utc).isoformat()
    #             stages[stage_name]["attempts"] = stages[stage_name].get("attempts", 0) + 1
    #             if execution_id:
    #                 stages[stage_name]["execution_id"] = execution_id
    #         elif status == "completed":
    #             stages[stage_name]["finished_at"] = datetime.now(timezone.utc).isoformat()
    #             if result_data:
    #                 stages[stage_name]["result"] = result_data
    #         elif status == "failed":
    #             stages[stage_name]["failed_at"] = datetime.now(timezone.utc).isoformat()
    #             if result_data and "error_message" in result_data:
    #                 stages[stage_name]["error_message"] = result_data["error_message"]
            
    #         status_dict["stages"] = stages
    #         document.status_dict = status_dict
    #         document.updated_at = datetime.now(timezone.utc)
            
    #         session.add(document)
    #         session.commit()
            
    #     except Exception as e:
    #         logger.error(f"Failed to update document stage status: {e}")

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