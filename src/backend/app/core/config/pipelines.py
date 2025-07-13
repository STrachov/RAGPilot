from app.core.models.pipeline import Pipeline, PipelineStage
from app.core.config.constants import PipelineStageType

# Standard RAG Pipeline (Parse -> Chunk -> Index)
standard_rag_pipeline = Pipeline(
    name="standard_rag",
    description="Standard RAG pipeline: Parse document, create chunks, and index for retrieval",
    version="1.0",
    stages=[
        PipelineStage(
            name="parse",
            stage_type=PipelineStageType.PARSE,
            function_name="parse_stage",
            config={},
            retry_attempts=2
        ),
        PipelineStage(
            name="chunk",
            stage_type=PipelineStageType.CHUNK,
            function_name="chunk_stage",
            config={},
            dependencies=[PipelineStageType.PARSE],
            retry_attempts=2
        ),
        PipelineStage(
            name="index",
            stage_type=PipelineStageType.INDEX,
            function_name="index_stage",
            config={},
            dependencies=[PipelineStageType.CHUNK],
            retry_attempts=2
        )
    ]
)

# Parse Only Pipeline (Parse only)
parse_only_pipeline = Pipeline(
    name="parse_only",
    description="Parse document only, skip chunking and indexing",
    version="1.0",
    stages=[
        PipelineStage(
            name="parse",
            stage_type=PipelineStageType.PARSE,
            function_name="parse_stage",
            config={},
            retry_attempts=3
        )
    ]
)

# Dictionary of all predefined pipelines
predefined_pipelines = {
    standard_rag_pipeline.name: standard_rag_pipeline,
    parse_only_pipeline.name: parse_only_pipeline,
} 