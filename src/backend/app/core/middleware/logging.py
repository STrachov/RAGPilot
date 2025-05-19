import time
import uuid
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logger import api_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request and response data"""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/api/health", "/metrics", "/docs", "/redoc"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Collect request data
        request_data = await self._get_request_data(request)
        api_logger.info(
            f"Request {request_id}: {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process the request through the application
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response information
            status_code = response.status_code
            api_logger.info(
                f"Response {request_id}: {request.method} {request.url.path} - "
                f"Status: {status_code} - Time: {process_time:.4f}s"
            )
            
            return response
            
        except Exception as e:
            # Log unhandled exceptions
            api_logger.exception(
                f"Unhandled exception in {request.method} {request.url.path}: {str(e)}"
            )
            # Re-raise the exception
            raise
    
    async def _get_request_data(self, request: Request) -> Dict:
        """Extract useful data from the request for logging"""
        # Get headers (excluding authorization)
        headers = dict(request.headers)
        if "authorization" in headers:
            headers["authorization"] = "[REDACTED]"
        
        return {
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": request.client.host if request.client else None,
            "headers": headers,
        } 