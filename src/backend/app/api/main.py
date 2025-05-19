from fastapi import APIRouter

from app.api.routes import auth, users, utils, documents, chat, admin, health

api_router = APIRouter()

# Main API routes with prefixes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])

# Health routes without prefix for root-level health checks
api_router.include_router(health.router, tags=["health"])

