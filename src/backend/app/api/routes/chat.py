from typing import Any, List, Optional
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, desc
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.core.models.monitoring import Query, Response, RetrievalResult, Feedback
from app.core.config.constants import (
    QueryStatus, 
    DEFAULT_LLM_CONFIG, 
    DEFAULT_RETRIEVAL_STRATEGY,
    DEFAULT_PROMPT_TEMPLATES
)

router = APIRouter()


class QueryRequest(BaseModel):
    """Request body for submitting a query"""
    query_text: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response for a query"""
    id: uuid.UUID
    response_text: str
    sources: List[str] = []
    created_at: datetime


class FeedbackRequest(BaseModel):
    """Request body for submitting feedback"""
    rating: Optional[int] = None
    feedback_text: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def submit_query(
    request: QueryRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Submit a question to the RAG system"""
    # Create a new query
    query = Query(
        user_id=current_user.id,
        query_text=request.query_text,
        session_id=request.session_id,
        status=QueryStatus.PROCESSING
    )
    session.add(query)
    session.commit()
    session.refresh(query)
    
    try:
        # In a real implementation, this would call your RAG pipeline
        # For now, we'll simulate the process
        
        # 1. Retrieve relevant chunks (simplified simulation)
        # In a real implementation, you would:
        # - Compute embeddings for the query
        # - Search vector store for relevant chunks
        # - Possibly use hybrid search with BM25
        
        # Simulated retrieval results - these would come from your retriever
        retrieval_results = []
        chunks_query = select(RetrievalResult).limit(3)  # Just a placeholder
        
        # 2. Generate response with LLM (simulated)
        # This would use the chunks to create a prompt for the LLM
        
        # Simulated LLM response
        response_text = f"This is a simulated response to: {request.query_text}"
        sources = ["doc1.pdf", "doc2.pdf"]  # These would be real document references
        
        # 3. Create response record
        response = Response(
            query_id=query.id,
            response_text=response_text,
            sources=sources
        )
        session.add(response)
        
        # 4. Update query status
        query.status = QueryStatus.COMPLETED
        query.completed_at = datetime.now(timezone.utc)
        session.add(query)
        session.commit()
        session.refresh(response)
        
        return QueryResponse(
            id=response.id,
            response_text=response.response_text,
            sources=response.sources,
            created_at=response.created_at
        )
        
    except Exception as e:
        # Update query status to failed
        query.status = QueryStatus.FAILED
        session.add(query)
        session.commit()
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@router.get("/history", response_model=List[QueryResponse])
async def get_chat_history(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 20,
    session_id: Optional[str] = None,
) -> Any:
    """Get chat history for the current user"""
    query = select(Response).join(Query).where(Query.user_id == current_user.id)
    
    if session_id:
        query = query.where(Query.session_id == session_id)
    
    query = query.order_by(desc(Response.created_at)).offset(skip).limit(limit)
    responses = session.exec(query).all()
    
    return [
        QueryResponse(
            id=response.id,
            response_text=response.response_text,
            sources=response.sources,
            created_at=response.created_at
        ) for response in responses
    ]


@router.post("/{response_id}/feedback")
async def submit_feedback(
    response_id: uuid.UUID,
    feedback_request: FeedbackRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Submit feedback for a response"""
    # Get the response
    response = session.get(Response, response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    
    # Create feedback
    feedback = Feedback(
        query_id=response.query_id,
        response_id=response_id,
        user_id=current_user.id,
        rating=feedback_request.rating,
        feedback_text=feedback_request.feedback_text
    )
    
    session.add(feedback)
    session.commit()
    
    return {"message": "Feedback submitted successfully"}


@router.get("/config")
async def get_chat_config(
    current_user: CurrentUser,
) -> Any:
    """Get configuration for the chat interface"""
    return {
        "llm_config": DEFAULT_LLM_CONFIG,
        "retrieval_strategy": DEFAULT_RETRIEVAL_STRATEGY,
        "prompt_templates": DEFAULT_PROMPT_TEMPLATES
    } 