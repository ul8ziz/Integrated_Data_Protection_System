"""
Database connection and session management for MongoDB
"""
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

# MongoDB client
client: AsyncIOMotorClient = None
database = None
_initialized = False


async def init_mongodb():
    """
    Initialize MongoDB connection and Beanie
    """
    global client, database, _initialized
    
    if _initialized:
        logger.info("MongoDB already initialized")
        return
    
    try:
        logger.info(f"Initializing MongoDB connection to {settings.MONGODB_URL}...")
        
        # Create MongoDB client with longer timeout
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,  # 5 seconds
            connectTimeoutMS=5000
        )
        
        # Test connection first (with timeout)
        try:
            await asyncio.wait_for(client.admin.command('ping'), timeout=5.0)
            logger.info("MongoDB connection test successful")
        except asyncio.TimeoutError:
            logger.error("MongoDB connection timeout - MongoDB may not be running")
            raise ConnectionError("MongoDB connection timeout")
        except Exception as ping_error:
            logger.error(f"MongoDB ping failed: {ping_error}")
            raise ConnectionError(f"MongoDB not accessible: {ping_error}")
        
        # Get database
        database = client[settings.MONGODB_DB_NAME]
        
        # Import all models BEFORE init_beanie
        from app.models_mongo import users, policies, alerts, logs
        
        logger.info("Initializing Beanie with document models...")
        
        # Initialize Beanie with all document models
        await init_beanie(
            database=database,
            document_models=[
                users.User,
                policies.Policy,
                alerts.Alert,
                logs.Log,
                logs.DetectedEntity
            ]
        )
        
        _initialized = True
        logger.info(f"MongoDB and Beanie initialized successfully: {settings.MONGODB_DB_NAME}")
        
    except ConnectionError as e:
        logger.error(f"MongoDB connection error: {e}")
        logger.error("=" * 60)
        logger.error("MongoDB is not running or not accessible!")
        logger.error("Please:")
        logger.error("  1. Install MongoDB from https://www.mongodb.com/try/download/community")
        logger.error("  2. Start MongoDB service (Windows: Services -> MongoDB)")
        logger.error("  3. Or run: mongod --dbpath C:\\data\\db")
        logger.error("=" * 60)
        _initialized = False
        # Don't raise - allow app to start but operations will fail
        client = None
        database = None
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        import traceback
        logger.error(traceback.format_exc())
        _initialized = False
        client = None
        database = None
        # Don't raise - allow app to start but operations will fail


def is_initialized():
    """Check if MongoDB is initialized"""
    return _initialized


async def close_mongodb():
    """
    Close MongoDB connection
    """
    global client, _initialized
    if client:
        client.close()
        _initialized = False
        logger.info("MongoDB connection closed")


def get_database():
    """
    Get MongoDB database instance
    """
    return database
