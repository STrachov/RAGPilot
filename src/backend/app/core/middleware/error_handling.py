from typing import Callable, Dict, Union

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import app_logger


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent error handling across the application"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except SQLAlchemyError as e:
            # Database errors
            app_logger.exception(f"Database error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Database error occurred", "type": "database_error"}
            )
        except Exception as e:
            # Unhandled exceptions
            app_logger.exception(f"Unhandled error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "An unexpected error occurred", "type": "server_error"}
            )


def add_error_handlers(app: FastAPI) -> None:
    """Add error handlers to the FastAPI application"""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle HTTP exceptions with consistent response format"""
        status_code = exc.status_code
        
        # Log client errors (4xx) as warnings, server errors (5xx) as errors
        if 400 <= status_code < 500:
            app_logger.warning(f"HTTP {status_code} error: {exc.detail}")
        else:
            app_logger.error(f"HTTP {status_code} error: {exc.detail}")
        
        return JSONResponse(
            status_code=status_code,
            content={"detail": exc.detail, "type": "http_error"}
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle validation errors with detailed feedback"""
        app_logger.warning(f"Validation error: {str(exc)}")
        
        # Format validation errors for better readability
        errors = []
        for error in exc.errors():
            error_detail = {
                "location": error["loc"],
                "message": error["msg"],
                "type": error["type"]
            }
            errors.append(error_detail)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "type": "validation_error",
                "errors": errors
            }
        ) 