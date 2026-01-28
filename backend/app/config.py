"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv
import os

# Load .env file from backend directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Secure Data Protection System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    
    # Database - MongoDB
    MONGODB_URL: str = os.getenv(
        "MONGODB_URL",
        "mongodb://localhost:27017"
    )
    MONGODB_DB_NAME: str = os.getenv(
        "MONGODB_DB_NAME",
        "Secure_db"
    )
    
    # Database - SQL (Legacy - للتوافق مع الكود القديم)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/Secure_db"
    )
    
    # Encryption
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY",
        "change-me-to-32-byte-key-in-production"
    )
    
    # Presidio
    PRESIDIO_LANGUAGE: str = os.getenv("PRESIDIO_LANGUAGE", "ar")
    PRESIDIO_SUPPORTED_ENTITIES: str = os.getenv(
        "PRESIDIO_SUPPORTED_ENTITIES",
        "PERSON,PHONE_NUMBER,EMAIL_ADDRESS,CREDIT_CARD,ADDRESS,ORGANIZATION"
    )
    
    # MyDLP
    # Force enable MyDLP by default - can be overridden by environment variable
    # Default to True if not explicitly set to False
    _mydlp_env = os.getenv("MYDLP_ENABLED", "").strip().lower()
    if _mydlp_env in ("false", "0", "no", "off"):
        MYDLP_ENABLED: bool = False
    else:
        # Default to True (if empty or any other value)
        MYDLP_ENABLED: bool = True
    MYDLP_API_URL: str = os.getenv("MYDLP_API_URL", "http://localhost:8080")
    MYDLP_API_KEY: str = os.getenv("MYDLP_API_KEY", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    
    # Timezone
    TIMEZONE: str = os.getenv("TIMEZONE", "UTC")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

