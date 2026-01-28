"""
Main FastAPI application
"""
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database_mongo import init_mongodb, close_mongodb
from app.api.routes import analysis, policies, alerts, monitoring
from app.api.routes import email_receiver, auth, users
from app.middleware.mongodb_check import MongoDBCheckMiddleware
from app.middleware.file_scanner import FileScannerMiddleware
import logging
import os

# Configure logging
os.makedirs("logs", exist_ok=True)

# Ensure UTF-8 output on Windows consoles to avoid UnicodeEncodeError for Arabic logs
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    # Don't block startup if console can't be reconfigured
    pass

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(stream=sys.stdout)
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

# MongoDB check middleware (after CORS)
app.add_middleware(MongoDBCheckMiddleware)

# File scanner middleware (after MongoDB check)
app.add_middleware(FileScannerMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(analysis.router)
app.include_router(policies.router)
app.include_router(alerts.router)
app.include_router(monitoring.router)
app.include_router(email_receiver.router)

# Test-only routes (only available when ENVIRONMENT=test)
import os
if os.getenv("ENVIRONMENT", "").lower() == "test":
    from app.api.routes import test_seed
    app.include_router(test_seed.router)

# Mount static files for frontend
try:
    # Get the project root directory (three levels up from app/main.py)
    # __file__ = backend/app/main.py
    # app_dir = backend/app
    # backend_dir = backend
    # project_root = Secure (project root)
    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(current_file)  # backend/app
    backend_dir = os.path.dirname(app_dir)   # backend
    project_root = os.path.dirname(backend_dir)  # Secure (project root)
    
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
        # Initialize MongoDB
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
        await init_mongodb()
        logger.info("MongoDB database initialized successfully")
        
        # Create default admin if doesn't exist (only if MongoDB is initialized)
        from app.database_mongo import is_initialized
        
        if is_initialized():
            from app.models_mongo.users import User, UserRole, UserStatus
            from app.services.auth_service import get_password_hash
            from app.utils.datetime_utils import get_current_time
            
            try:
                admin = await User.find_one({"role": UserRole.ADMIN.value})
                if not admin:
                    logger.info("Creating default admin user...")
                    admin_password = "admin123"
                    hashed_password = get_password_hash(admin_password)
                    admin_user = User(
                        username="admin",
                        email="admin@example.com",
                        hashed_password=hashed_password,
                        role=UserRole.ADMIN,
                        status=UserStatus.ACTIVE,
                        is_active=True,
                        approved_at=get_current_time()
                    )
                    await admin_user.insert()
                    logger.info("Default admin created: username=admin, password=admin123")
                else:
                    logger.info(f"Admin user already exists: {admin.username}")
            except Exception as e:
                logger.error(f"Error creating/checking admin user: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Create default policy if it doesn't exist
            try:
                from app.scripts.create_default_policy import create_default_policy
                await create_default_policy()
            except Exception as e:
                logger.error(f"Error creating default policy: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("Skipping admin user creation - MongoDB not initialized")
    except Exception as e:
        logger.error(f"CRITICAL: Error initializing database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Don't raise - allow app to start but log the error
        logger.warning("=" * 60)
        logger.warning("⚠️  WARNING: MongoDB is not connected!")
        logger.warning("The application will start, but database operations will fail.")
        logger.warning("")
        logger.warning("To fix this:")
        logger.warning("  1. Install MongoDB from https://www.mongodb.com/try/download/community")
        logger.warning("  2. Start MongoDB service (Windows: Services -> MongoDB)")
        logger.warning("  3. Or run: mongod --dbpath C:\\data\\db")
        logger.warning("  4. Then restart this application")
        logger.warning("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await close_mongodb()
    logger.info("Application shutdown complete")


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
    from app.database_mongo import is_initialized, client
    from app.utils.datetime_utils import get_current_time
    
    mongodb_status = "connected" if is_initialized() else "disconnected"
    status = "healthy" if is_initialized() else "degraded"
    
    return {
        "status": status,
        "mongodb": {
            "status": mongodb_status,
            "initialized": is_initialized(),
            "message": "MongoDB is connected and ready" if is_initialized() else "MongoDB is not connected. Please start MongoDB service."
        },
        "timestamp": get_current_time().isoformat()
    }

