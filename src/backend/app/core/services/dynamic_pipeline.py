"""
Dynamic Pipeline Service
Main service that manages pipelines, registers stages, and provides predefined pipelines
"""

from typing import Dict, Any, Optional, List
from sqlmodel import Session
import asyncio
from datetime import datetime, timezone

from app.core.models.pipeline import Pipeline, PipelineStage, PipelineStageType, PipelineExecution
from app.core.services.stage_registry import stage_registry
from app.core.services.pipeline_executor import pipeline_executor
from app.core.services.document_stages import DocumentStages
from app.core.config.pipelines import predefined_pipelines
from app.core.logger import app_logger as logger


class DynamicPipelineService:
    """Main service for managing pipelines and stage execution"""
    
    def __init__(self):
        self.document_stages = DocumentStages()
        self.predefined_pipelines: Dict[str, Pipeline] = {}
        self._initialized = False
    
    def _register_stages(self) -> None:
        """Register all available pipeline stages"""
        
        # Register parse stage
        stage_registry.register_stage(
            name="parse_stage",
            func=self.document_stages.parse_stage,
            description="Parse document using RAGParser",
            timeout_seconds=1800  # 30 minutes
        )
        
        # Register chunk stage
        stage_registry.register_stage(
            name="chunk_stage",
            func=self.document_stages.chunk_stage,
            dependencies=["parse"],
            description="Split document into chunks",
            timeout_seconds=600  # 10 minutes
        )
        
        # Register index stage
        stage_registry.register_stage(
            name="index_stage",
            func=self.document_stages.index_stage,
            dependencies=["chunk"],
            description="Index document chunks for retrieval",
            timeout_seconds=900  # 15 minutes
        )
        # TODO: Delete thee chunk_index stage
        # Register combined chunk+index stage
        stage_registry.register_stage(
            name="chunk_index_stage",
            func=self.document_stages.chunk_index_stage,
            dependencies=["parse"],
            description="Combined chunking and indexing",
            timeout_seconds=1200  # 20 minutes
        )
        
        # Register graph creation stage
        stage_registry.register_stage(
            name="create_graph_stage",
            func=self.document_stages.create_graph_stage,
            dependencies=["chunk"],
            description="Create knowledge graph from document",
            timeout_seconds=1800  # 30 minutes
        )
        
        logger.info(f"Registered {len(stage_registry.list_stages())} stages")
    
    def _load_predefined_pipelines(self) -> None:
        """Load predefined pipelines from the configuration."""
        self.predefined_pipelines = predefined_pipelines
        logger.info(f"Loaded {len(self.predefined_pipelines)} predefined pipelines")

    def initialize(self) -> None:
        """Initialize the pipeline service by registering stages and creating predefined pipelines"""
        if self._initialized:
            return
        
        logger.info("Initializing Dynamic Pipeline Service...")
        
        # Register all available stages
        self._register_stages()
        
        # Load predefined pipelines
        self._load_predefined_pipelines()
        
        self._initialized = True
        logger.info("Dynamic Pipeline Service initialized successfully")
    
    async def execute_pipeline(
        self,
        pipeline_name: str,
        document_id: str,
        session: Session,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> PipelineExecution:
        """Execute a predefined pipeline"""
        self.initialize()
        
        if pipeline_name not in self.predefined_pipelines:
            raise ValueError(f"Unknown pipeline: {pipeline_name}. Available: {list(self.predefined_pipelines.keys())}")
        
        pipeline = self.predefined_pipelines[pipeline_name]
        return await pipeline_executor.execute_pipeline(
            pipeline=pipeline,
            document_id=document_id,
            session=session,
            config_overrides=config_overrides
        )
    
    async def execute_single_stage(
        self,
        document_id: str,
        stage_name: str,
        session: Session,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a single stage (backward compatibility)"""
        self.initialize()
        
        # Create a single-stage pipeline
        single_stage_pipeline = Pipeline(
            name=f"single_{stage_name}",
            description=f"Single stage execution: {stage_name}",
            stages=[
                PipelineStage(
                    name=stage_name,
                    stage_type=PipelineStageType[stage_name.upper()],
                    function_name=f"{stage_name}_stage",
                    config=config or {}
                )
            ]
        )
        
        execution = await pipeline_executor.execute_pipeline(
            pipeline=single_stage_pipeline,
            document_id=document_id,
            session=session
        )
        
        if execution.error_message:
            raise Exception(execution.error_message)
        
        return execution.stage_results.get(stage_name, {})
    
    def get_predefined_pipelines(self) -> Dict[str, Pipeline]:
        """Get all predefined pipelines"""
        self.initialize()
        return self.predefined_pipelines

    def get_pipeline(self, pipeline_name: str) -> Optional[Pipeline]:
        """Get a specific predefined pipeline by name"""
        self.initialize()
        return self.predefined_pipelines.get(pipeline_name)
    
    def get_available_stages(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available stages"""
        self.initialize()
        return stage_registry.get_stage_info()

    async def continue_pipeline(
        self,
        document_id: str,
        pipeline_name: str,
        stage_execution_id: str,
        result: Dict[str, Any],
        session: Session,
    ) -> None:
        """Continue a pipeline from a completed stage"""
        logger.info(f"Continuing pipeline '{pipeline_name}' for document {document_id} from stage execution {stage_execution_id}")

        document = session.get(Document, document_id)
        if not document:
            logger.error(f"Document {document_id} not found for pipeline continuation")
            return
            
        pipeline = self.get_pipeline(pipeline_name)
        if not pipeline:
            logger.error(f"Pipeline '{pipeline_name}' not found for document {document_id}")
            return

        # Find the execution and update its status
        status_dict = document.status_dict
        completed_stage_name = None
        if "stages" in status_dict:
            for stage_name, stage_data in status_dict["stages"].items():
                if "executions" in stage_data:
                    for execution in stage_data["executions"]:
                        if execution.get("stage_execution_id") == stage_execution_id:
                            execution["status"] = result.get("status", "completed")
                            execution["completed_at"] = datetime.now(timezone.utc).isoformat()
                            execution["result"] = result
                            completed_stage_name = stage_name
                            # Update top-level stage status
                            stage_data["status"] = execution["status"]
                            stage_data["result"] = result
                            break
                if completed_stage_name:
                    break
        
        if not completed_stage_name:
            logger.error(f"Stage execution {stage_execution_id} not found for document {document_id}")
            return
            
        document.status_dict = status_dict
        session.add(document)
        session.commit()
        
        # Now, trigger the pipeline executor to check for the next stages
        await pipeline_executor.execute_pipeline(
            pipeline=pipeline,
            document_id=document_id,
            session=session,
            # We pass the execution_id from the context of the initial pipeline run if it exists
            # This is not implemented yet, so we pass None
            execution_id=None 
        )


# Global pipeline service instance
dynamic_pipeline_service = DynamicPipelineService() 