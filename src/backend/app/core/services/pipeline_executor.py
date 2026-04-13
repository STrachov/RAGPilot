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
    PipelineStageStatus
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
                execution.finished_at = datetime.now(timezone.utc).isoformat()
                return execution
            
            # Get document
            document = session.get(Document, document_id)
            if not document:
                error_msg = f"Document {document_id} not found"
                logger.error(error_msg)
                execution.error_message = error_msg
                execution.failed_stage = "document_lookup"
                execution.finished_at = datetime.now(timezone.utc).isoformat()
                return execution
            
            # Initialize all stage statuses
            for stage in pipeline.stages:
                execution.stage_statuses[stage.name] = PipelineStageStatus.WAITING
            
            # Execute pipeline sequentially for now (can add parallel later)
            await self._execute_pipeline_sequential(pipeline, document, session, execution, config_overrides)
            
            execution.finished_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Pipeline '{pipeline.name}' execution {execution_id} completed")
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            execution.error_message = error_msg
            execution.finished_at = datetime.now(timezone.utc).isoformat()
        
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
        logger.info(f"All stages len: {len(all_stages)}")
        # Find stages that are ready to run
        ready_stages = []
        for stage_name, stage in all_stages.items():
            # Skip if already completed or currently running
            if stage_name in completed_stages:
                logger.info(f"Stage {stage_name} skipped because it is already completed")
                continue
            if doc_stages.get(stage_name, {}).get("status") == "running":
                logger.info(f"Stage {stage_name} skipped because it is already running")
                continue

            if all(dep in completed_stages for dep in stage.dependencies):
                ready_stages.append(stage)
        logger.info(f"Ready stages len: {len(ready_stages)}")

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
        
        # Execute only the first stage
        stage = ready_stages[0]
        stage.stage_id = str(uuid.uuid4())
        await self._execute_single_stage(stage, document, session, execution, config_overrides)
        
        
        
    
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
            #"callback_url": f"{settings.SERVER_HOST.rstrip('/')}{settings.API_V1_STR}/hooks/stage_completion",
            "callback_url": f"{settings.SERVER_HOST.rstrip('/')}/api/hooks/stage_completion",
            
            "document_id": document.id,
            "execution_id": execution.execution_id,
            "pipeline_name": execution.pipeline_name,
            "stage_name": execution.current_stage,
            "stage_id": stage.stage_id
            #"previous_results": execution.stage_results
        }

        # Apply config overrides
        final_config = {**stage.config}
        if config_overrides and stage.name in config_overrides:
            final_config.update(config_overrides[stage.name])
        
        # Create modified stage with final config
        stage_to_execute = PipelineStage(
            name=stage.name,
            stage_id=stage.stage_id,
            stage_type=stage.stage_type,
            function_name=stage.function_name,
            config=final_config,
            dependencies=stage.dependencies,
            optional=stage.optional,
            retry_attempts=stage.retry_attempts,
            timeout_seconds=stage.timeout_seconds
        )
        
        # Execute with retries
        stage_result_data = {}
        start_time = datetime.now(timezone.utc).isoformat()
        try:
            stage_result = await stage_registry.execute_stage(
                stage_to_execute, document, session, context
            )
            logger.info(f"Stage '{stage.name}' was run with context {str(context)}")

            execution.stage_statuses[stage.name] = PipelineStageStatus.RUNNING  
            stage_result_data = stage_result.model_dump()
            logger.info(f"Stage '{stage.name}' result: {str(stage_result_data)}")
                
        except Exception as e:
            execution.stage_statuses[stage.name] = PipelineStageStatus.FAILED 
            stage_result_data['status'] = PipelineStageStatus.FAILED.value
            stage_result_data['started_at'] = start_time
            stage_result_data['finished_at'] = datetime.now(timezone.utc).isoformat()
            stage_result_data['result'] = None
            stage_result_data["error_message"]= str(e)

            logger.error(f"Stage '{stage.name}' failed with error {str(e)}")
        
        # Update document status to reflect current stage
        await self._update_document_stage_status(
            document,
            session,
            stage_to_execute,
            execution,
            stage_result_data,
        )

        
    async def _update_document_stage_status(
        self,
        document: Document,
        session: Session,
        stage: PipelineStage,
        execution: PipelineExecution,
        result_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update the document's stage status"""
        stage_name = stage.name
        status = execution.stage_statuses[stage.name]
        execution_id = execution.execution_id
        
        logger.info(f"Updating document stage status for stage {stage_name} with status {status}")
        try:
            status_dict = document.status_dict
            stages = status_dict.get("stages", {})
            
            if stage_name not in stages:
                stages[stage_name] = {}
            
            stages[stage_name]["status"] = status
            if result_data and "finished_at" in result_data:
                stages[stage_name]["finished_at"] = result_data["finished_at"]

            #stages[stage_name]["attempts"] = stages[stage_name].get("attempts", 0) + 1
            
            if stage.stage_id:
                stages[stage_name]["stage_id"] = stage.stage_id

            if execution_id:
                stages[stage_name]["execution_id"] = execution_id
            
            if result_data and "result" in result_data:
                stages[stage_name]["result"] = result_data["result"]
                
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