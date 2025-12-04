"""
API routers for the unified service
"""
from .health import router as health_router
from .documents import router as documents_router
from .chat import router as chat_router
from .dialogs import router as dialogs_router

__all__ = [
    "health_router",
    "documents_router",
    "chat_router",
    "dialogs_router"
]

