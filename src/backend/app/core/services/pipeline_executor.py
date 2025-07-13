"""
Pipeline Executor Service
Orchestrates the execution of complete pipelines with dependency resolution
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone
from sqlmodel import Session

from app.core.models.document import Document
from app.core.models.pipeline import (
    Pipeline, PipelineStage, PipelineExecution, 
    StageResult, StageStatus, PipelineStageType
)
from app.core.services.stage_registry import stage_registry
from app.core.logger import app_logger as logger
from app.core.config.settings import settings

class PipelineExecutor:
    """Orchestrates pipeline execution with dependency resolution"""
    
    def __init__(self):
        self.active_executions: Dict[str, PipelineExecution] = {}
    
    async def execute_pipeline(
        self,
        pipeline: Pipeline,
        document_id: str,
        session: Session,
        config_overrides: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> PipelineExecution:
        """Execute a complete pipeline for a document"""
        
        # Create execution tracking
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        execution = PipelineExecution(
            pipeline_name=pipeline.name,
            document_id=document_id,
            execution_id=execution_id,
            started_at=datetime.now(timezone.utc).isoformat()
        )
        
        self.active_executions[execution_id] = execution
        
        try:
            logger.info(f"Starting pipeline '{pipeline.name}' execution {execution_id} for document {document_id}")
            
            # Validate pipeline
            validation_errors = pipeline.validate_dependencies()
            registry_errors = stage_registry.validate_dependencies(pipeline.stages)
            
            all_errors = validation_errors + registry_errors
            if all_errors:
                error_msg = "Pipeline validation failed: " + "; ".join(all_errors)
                logger.error(error_msg)
                execution.error_message = error_msg
                execution.failed_stage = "validation"
                execution.completed_at = datetime.now(timezone.utc).isoformat()
                return execution
            
            # Get document
            document = session.get(Document, document_id)
            if not document:
                error_msg = f"Document {document_id} not found"
                logger.error(error_msg)
                execution.error_message = error_msg
                execution.failed_stage = "document_lookup"
                execution.completed_at = datetime.now(timezone.utc).isoformat()
                return execution
            
            # Initialize all stage statuses
            for stage in pipeline.stages:
                execution.stage_statuses[stage.name] = StageStatus.WAITING
            
            # Execute pipeline sequentially for now (can add parallel later)
            await self._execute_pipeline_sequential(pipeline, document, session, execution, config_overrides)
            
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Pipeline '{pipeline.name}' execution {execution_id} completed")
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            execution.error_message = error_msg
            execution.completed_at = datetime.now(timezone.utc).isoformat()
        
        finally:
            # Clean up active execution tracking
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
        
        return execution
    
    async def _execute_pipeline_sequential(
        self,
        pipeline: Pipeline,
        document: Document,
        session: Session,
        execution: PipelineExecution,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Execute all currently ready stages in a pipeline based on dependencies."""
        
        completed_stages: Set[str] = set()
        doc_stages = document.status_dict.get("stages", {})
        # for stage_name, stage_data in doc_stages.items():
        #     if stage_data.get("status") == "completed":
        #         completed_stages.add(stage_name)
        
        all_stages = {stage.name: stage for stage in pipeline.stages}
        
        # Find stages that are ready to run
        ready_stages = []
        for stage_name, stage in all_stages.items():
            # Skip if already completed or currently running
            if stage_name in completed_stages or doc_stages.get(stage_name, {}).get("status") == "running":
                continue
            
            if all(dep in completed_stages for dep in stage.dependencies):
                ready_stages.append(stage)

        if not ready_stages:
            logger.info(f"No more stages ready to execute for document {document.id} in pipeline {pipeline.name}")
            return
            
        logger.info(f"Executing ready stages: {[s.name for s in ready_stages]} for document {document.id}")
        
        # Execute all ready stages concurrently
        # tasks = [
        #     self._execute_single_stage(stage, document, session, execution, config_overrides)
        #     for stage in ready_stages
        # ]
        # await asyncio.gather(*tasks)
        self._execute_single_stage(ready_stages[0], document, session, execution, config_overrides)
    
    async def _execute_single_stage(
        self,
        stage: PipelineStage,
        document: Document,
        session: Session,
        execution: PipelineExecution,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Execute a single stage with retries"""
        
        execution.current_stage = stage.name

        # Prepare execution context
        context = {
            "callback_url": f"{settings.SERVER_HOST.rstrip('/')}{settings.API_V1_STR}/hooks/stage_completion",
            "document_id": document.id,
            "execution_id": execution.execution_id,
            "pipeline_name": execution.pipeline_name,
            "stage_name": execution.current_stage
            #"previous_results": execution.stage_results
        }

        # Apply config overrides
        final_config = {**stage.config}
        if config_overrides and stage.name in config_overrides:
            final_config.update(config_overrides[stage.name])
        
        # Create modified stage with final config
        stage_to_execute = PipelineStage(
            name=stage.name,
            stage_type=stage.stage_type,
            function_name=stage.function_name,
            config=final_config,
            dependencies=stage.dependencies,
            optional=stage.optional,
            retry_attempts=stage.retry_attempts,
            timeout_seconds=stage.timeout_seconds
        )
        
        # Execute with retries
        result_data = {}
        try:
            result = await stage_registry.execute_stage(
                stage_to_execute, document, session, context
            )
            logger.info(f"Stage '{stage.name}' was run with context {str(context)}")

            execution.stage_statuses[stage.name] = StageStatus.RUNNING  
            result_data = result.model_dump()
            logger.info(f"Stage '{stage.name}' result: {str(result_data)}")
                
        except Exception as e:
            execution.stage_statuses[stage.name] = StageStatus.FAILED  
            result_data["error_message"]= str(e)
            logger.info(f"Stage '{stage.name}' failed with error {str(e)}")
        
        # Update document status to reflect current stage
        await self._update_document_stage_status(
            document,
            session,
            stage.name,
            execution.stage_statuses[stage.name],
            execution.execution_id,
            result_data,
        )

        
    async def _update_document_stage_status(
        self,
        document: Document,
        session: Session,
        stage_name: str,
        status: str,
        execution_id: str,
        result_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update the document's stage status"""
        try:
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            
            if stage_name not in stages:
                stages[stage_name] = {}
            
            stages[stage_name]["status"] = status
            if status == "running":
                stages[stage_name]["started_at"] = datetime.now(timezone.utc).isoformat()
                stages[stage_name]["attempts"] = stages[stage_name].get("attempts", 0) + 1
                if execution_id:
                    stages[stage_name]["execution_id"] = execution_id
            elif status == "completed":
                stages[stage_name]["completed_at"] = datetime.now(timezone.utc).isoformat()
                if result_data:
                    stages[stage_name]["result"] = result_data
            elif status == "failed":
                stages[stage_name]["failed_at"] = datetime.now(timezone.utc).isoformat()
                if result_data and "error_message" in result_data:
                    stages[stage_name]["error_message"] = result_data["error_message"]
            
            status_dict["stages"] = stages
            document.status_dict = status_dict
            document.updated_at = datetime.now(timezone.utc)
            
            session.add(document)
            session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update document stage status: {e}")
    
    def get_execution_status(self, execution_id: str) -> Optional[PipelineExecution]:
        """Get the status of a running execution"""
        return self.active_executions.get(execution_id)
    
    def list_active_executions(self) -> List[str]:
        """Get list of active execution IDs"""
        return list(self.active_executions.keys())


# Global executor instance
pipeline_executor = PipelineExecutor() 