from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session
from typing import Dict, Any, Optional

from app.api.deps import SessionDep
from app.core.models.document import Document
from app.core.services.dynamic_pipeline import dynamic_pipeline_service
from app.core.logger import app_logger as logger

router = APIRouter()


class StageCompletionPayload(BaseModel):
    document_id: str
    pipeline_name: str
    stage_id: str
    stage_name: str
    stage_status: str
    error_message: Optional[str] = None


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
    
    document_stages = document.status_dict["stages"]
    document_stage = document_stages[payload.stage_name]
    logger.info(f"Document stages dict: {document_stages}")
    logger.info(f"Is current stage in document's stages: {payload.stage_name in document_stages}")
    
    if payload.stage_name not in document_stages:
        logger.error(f"Stage name does not match the document's stages: {payload.stage_name} not in {document_stages}")
        raise HTTPException(status_code=400, detail="Stage name does not match the document's stages")
    
    if "stage_id" not in document_stage:
        logger.error(f"Stage ID does not exist in document's stages: {document_stage}")
        raise HTTPException(status_code=400, detail="Stage ID does not exist in document's stages")
    
    if payload.stage_id != document_stage["stage_id"]:
        logger.error(f"Stage ID does not match the current stage: {payload.stage_id} not in {document_stages}")
        raise HTTPException(status_code=400, detail="Stage ID does not match the current stage")
    
    document_stage.status = payload.stage_status
    if payload.stage_status != "completed":
        document_stage.error_message = payload.error_message
        logger.error(f"Stage status is not completed: {payload.stage_status}")
        error_messages = ["Stage status is not completed."]
        try:
            session.add(document)
            session.commit()
            error_messages.append("Stage status is updated successfully.")
        
        except Exception as e:
            error_messages.append(f"Error updating stage status.")
            logger.error(f"Error updating stage status: {e}")

        raise HTTPException(status_code=500, detail=" ".join(error_messages)) 
    
    document_stage.status = payload.stage_status
    session.add(document_stage)
    session.commit()
    
    next_stage_id = document_stages[payload.stage_id]["next_stage_id"]
    if next_stage_id is None:
        logger.info(f"No next stage found for {payload.stage_id}")
        return {"message": "No next stage found"}
    logger.info(f"Document's ")
    # background_tasks.add_task(
    #     dynamic_pipeline_service.continue_pipeline,
    #     document_id=payload.document_id,
    #     pipeline_name=payload.pipeline_name,
    #     stage_id=payload.stage_id,
    #     session=session,
    # )

    return {"message": "Callback received and processing initiated."} 