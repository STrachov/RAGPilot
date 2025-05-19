from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "RAGPilot API is running",
        "version": "0.1.0"
    }


@router.get("/health")
async def health():
    """Health check endpoint for load balancer/monitoring"""
    return {
        "status": "ok",
        "api": "running"
    } 