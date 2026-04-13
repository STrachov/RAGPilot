from app.core.models.pipeline import Pipeline, PipelineStage
from app.core.models.pipeline import PipelineStageType

#Stages
predefined_stages = {}
predefined_stages['parse'] = PipelineStage(
            name="parse",
            stage_type=PipelineStageType.PARSE,
            function_name="parse_stage",
            config={},
            #dependencies=[PipelineStageType.UPLOAD],
            retry_attempts=2,
            timeout_seconds=1200,
            description="Parse document using RAGParser"
        )
predefined_stages['chunk'] = PipelineStage(
            name="chunk",
            stage_type=PipelineStageType.CHUNK,
            function_name="chunk_stage",
            config={},
            dependencies=[PipelineStageType.PARSE],
            retry_attempts=2,
            timeout_seconds=1200,
            description="Split document into chunks"
        )
predefined_stages['index'] = PipelineStage(
            name="index",
            stage_type=PipelineStageType.INDEX,
            function_name="index_stage",
            config={},
            dependencies=[PipelineStageType.CHUNK],
            retry_attempts=2,
            timeout_seconds=1200,
            description="Index document chunks for retrieval"
        )
# Standard RAG Pipeline (Parse -> Chunk -> Index)
standard_rag_pipeline = Pipeline(
    name="standard_rag",
    title="Standard RAG Pipeline",
    description="Standard RAG pipeline: Parse document, create chunks, and index for retrieval",
    version="1.0",
    stages=[
        predefined_stages['parse'],
        predefined_stages['chunk'],
        predefined_stages['index']
    ]
)

# Parse Only Pipeline (Parse only)
parse_only_pipeline = Pipeline(
    name="parse_only",
    title="Parse Only Pipeline",
    description="Parse document only, skip chunking and indexing",
    version="1.0",
    stages=[
        predefined_stages['parse']
    ]
)

# Dictionary of all predefined pipelines
predefined_pipelines = {
    standard_rag_pipeline.name: standard_rag_pipeline,
    parse_only_pipeline.name: parse_only_pipeline,
} 