"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Athier Data Protection System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/athier_db"
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
    MYDLP_ENABLED: bool = os.getenv("MYDLP_ENABLED", "true").lower() == "true"
    MYDLP_API_URL: str = os.getenv("MYDLP_API_URL", "http://localhost:8080")
    MYDLP_API_KEY: str = os.getenv("MYDLP_API_KEY", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

