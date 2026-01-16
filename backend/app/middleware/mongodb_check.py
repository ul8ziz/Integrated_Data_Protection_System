"""
Middleware to check MongoDB initialization before processing requests
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.database_mongo import is_initialized
import logging

logger = logging.getLogger(__name__)


class MongoDBCheckMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure MongoDB is initialized before processing requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip check for health endpoint and static files
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/", "/static"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Check if MongoDB is initialized
        if not is_initialized():
            logger.error(f"MongoDB not initialized - rejecting request to {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": "Database not initialized. MongoDB is not running or not accessible.",
                    "error": "MongoDB connection failed",
                    "solution": "Please install and start MongoDB. See MONGODB_QUICK_START.md for instructions.",
                    "help_url": "https://www.mongodb.com/try/download/community"
                }
            )
        
        return await call_next(request)
