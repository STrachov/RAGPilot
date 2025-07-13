from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.core.config.constants import StageStatus, PipelineStageType
from app.core.models.document import DocumentStageInfo


class PipelineStage(BaseModel):
    """Definition of a single pipeline stage"""
    name: str = Field(..., description="Unique name for this stage")
    stage_type: PipelineStageType = Field(..., description="Type of stage")
    function_name: str = Field(..., description="Method name to execute for this stage")
    config: Dict[str, Any] = Field(default_factory=dict, description="Stage-specific configuration")
    dependencies: List[str] = Field(default_factory=list, description="List of stage names that must complete before this stage")
    optional: bool = Field(default=False, description="Whether this stage can be skipped if dependencies fail")
    retry_attempts: int = Field(default=1, description="Number of retry attempts for failed stages")
    timeout_seconds: Optional[int] = Field(default=None, description="Timeout for stage execution")
    
    class Config:
        use_enum_values = True


class Pipeline(BaseModel):
    """Definition of a complete processing pipeline"""
    name: str = Field(..., description="Unique name for this pipeline")
    description: str = Field(default="", description="Description of what this pipeline does")
    version: str = Field(default="1.0", description="Pipeline version")
    stages: List[PipelineStage] = Field(..., description="Ordered list of stages in this pipeline")
    default_config: Dict[str, Any] = Field(default_factory=dict, description="Default configuration for all stages")
    allow_parallel: bool = Field(default=False, description="Whether stages without dependencies can run in parallel")
    
    def get_stage_by_name(self, name: str) -> Optional[PipelineStage]:
        """Get a stage by its name"""
        return next((stage for stage in self.stages if stage.name == name), None)
    
    def get_dependencies_for_stage(self, stage_name: str) -> List[str]:
        """Get the list of dependencies for a given stage"""
        stage = self.get_stage_by_name(stage_name)
        return stage.dependencies if stage else []
    
    def validate_dependencies(self) -> List[str]:
        """Validate that all dependencies exist and there are no circular dependencies"""
        errors = []
        stage_names = {stage.name for stage in self.stages}
        
        # Check that all dependencies exist
        for stage in self.stages:
            for dep in stage.dependencies:
                if dep not in stage_names:
                    errors.append(f"Stage '{stage.name}' depends on non-existent stage '{dep}'")
        
        # Check for circular dependencies using DFS
        def has_cycle(stage_name: str, visiting: set, visited: set) -> bool:
            if stage_name in visiting:
                return True
            if stage_name in visited:
                return False
            
            visiting.add(stage_name)
            stage = self.get_stage_by_name(stage_name)
            if stage:
                for dep in stage.dependencies:
                    if has_cycle(dep, visiting, visited):
                        return True
            visiting.remove(stage_name)
            visited.add(stage_name)
            return False
        
        visited = set()
        for stage in self.stages:
            if stage.name not in visited:
                if has_cycle(stage.name, set(), visited):
                    errors.append(f"Circular dependency detected involving stage '{stage.name}'")
        
        return errors


class PipelineExecution(BaseModel):
    """Runtime information for a pipeline execution"""
    pipeline_name: str
    document_id: str
    execution_id: str
    stage_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    stage_statuses: Dict[str, StageStatus] = Field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_stage: Optional[str] = None
    failed_stage: Optional[str] = None
    error_message: Optional[str] = None
    
    def get_stage_result(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """Get the result data from a completed stage"""
        return self.stage_results.get(stage_name)
    
    def get_stage_status(self, stage_name: str) -> StageStatus:
        """Get the current status of a stage"""
        return self.stage_statuses.get(stage_name, StageStatus.WAITING)
    
    def is_stage_completed(self, stage_name: str) -> bool:
        """Check if a stage has completed successfully"""
        return self.get_stage_status(stage_name) == StageStatus.COMPLETED
    
    def are_dependencies_satisfied(self, stage: PipelineStage) -> bool:
        """Check if all dependencies for a stage are satisfied"""
        for dep in stage.dependencies:
            if not self.is_stage_completed(dep):
                return False
        return True

class StageResult(DocumentStageInfo):
    """Result of executing a single stage"""
    pass
