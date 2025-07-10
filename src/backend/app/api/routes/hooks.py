from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session
from typing import Dict, Any

from app.api.deps import SessionDep
from app.core.models.document import Document
from app.core.services.dynamic_pipeline import dynamic_pipeline_service
from app.core.logger import app_logger as logger

router = APIRouter()


class StageCompletionPayload(BaseModel):
    document_id: str
    stage_execution_id: str
    pipeline_name: str
    result: Dict[str, Any]


@router.post("/stage_completion")
async def handle_stage_completion(
    payload: StageCompletionPayload,
    session: SessionDep,
    background_tasks: BackgroundTasks,
):
    """
    Webhook endpoint for asynchronous stages to report completion.
    This endpoint will trigger the next stage in the pipeline.
    """
    logger.info(f"Received stage completion callback: {payload}")

    document = session.get(Document, payload.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # This is where the logic to find the next stage and trigger it will go.
    # For now, we'll just log it.
    
    background_tasks.add_task(
        dynamic_pipeline_service.continue_pipeline,
        document_id=payload.document_id,
        pipeline_name=payload.pipeline_name,
        stage_execution_id=payload.stage_execution_id,
        result=payload.result,
        session=session,
    )

    return {"message": "Callback received and processing initiated."} 