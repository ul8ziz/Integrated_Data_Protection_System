"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db
from app.api.routes import analysis, policies, alerts, monitoring
from app.api.routes import email_receiver
import logging
import os

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="نظام متكامل لحماية البيانات الشخصية - Integrated Data Protection System",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analysis.router)
app.include_router(policies.router)
app.include_router(alerts.router)
app.include_router(monitoring.router)
app.include_router(email_receiver.router)

# Mount static files for frontend
try:
    # Get the project root directory (three levels up from app/main.py)
    # __file__ = backend/app/main.py
    # app_dir = backend/app
    # backend_dir = backend
    # project_root = athier (project root)
    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(current_file)  # backend/app
    backend_dir = os.path.dirname(app_dir)   # backend
    project_root = os.path.dirname(backend_dir)  # athier (project root)
    
    static_dir = os.path.join(project_root, "frontend", "static")
    logger.info(f"Static files directory: {static_dir}")
    logger.info(f"Static directory exists: {os.path.exists(static_dir)}")
    
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Static files mounted successfully at /static")
    else:
        logger.warning(f"Static directory not found: {static_dir}")
        # Try alternative path (if running from backend directory)
        alt_static_dir = os.path.join(backend_dir, "frontend", "static")
        if os.path.exists(alt_static_dir):
            app.mount("/static", StaticFiles(directory=alt_static_dir), name="static")
            logger.info(f"Static files mounted from alternative path: {alt_static_dir}")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")
    import traceback
    logger.warning(traceback.format_exc())


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - serve frontend or API info"""
    from fastapi.responses import FileResponse, HTMLResponse
    import os
    
    # Get the project root directory (two levels up from app/main.py)
    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(current_file)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)
    
    static_dir = os.path.join(project_root, "frontend", "static")
    index_path = os.path.join(static_dir, "index.html")
    
    logger.info(f"Looking for index.html at: {index_path}")
    logger.info(f"File exists: {os.path.exists(index_path)}")
    
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    
    # Fallback to JSON if HTML not found
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
        "frontend": "Frontend not found. Please check frontend/static/index.html"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

