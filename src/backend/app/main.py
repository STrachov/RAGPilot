import logging
import os
import sys
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config.settings import settings
from app.core.logger import app_logger
from app.core.middleware.logging import RequestLoggingMiddleware
from app.core.middleware.error_handling import ErrorHandlingMiddleware, add_error_handlers
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/auth/login")

def custom_generate_unique_id(route: APIRoute) -> str:
    if route.tags and len(route.tags) > 0:
        return f"{route.tags[0]}-{route.name}"
    return f"api-{route.name}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    app_logger.info(f"Starting {settings.PROJECT_NAME} application")
    yield
    # Shutdown
    app_logger.info(f"Shutting down {settings.PROJECT_NAME} application")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RAGPilot: Advanced Document Q&A Platform with RAG",
    version="0.1.0",
    contact={
        "name": "RAGPilot Team",
        "url": "https://github.com/yourusername/ragpilot",
    },
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# Add error handlers
add_error_handlers(app)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        #allow_origins=settings.all_cors_origins,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix="/api")

# uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
# uvicorn app.main:app --host 127.0.0.1 --port 880 --reload --log-level debug