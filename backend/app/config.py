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
        "PERSON,PHONE_NUMBER,EMAIL_ADDRESS,CREDIT_CARD,ADDRESS,ORGANIZATION,DATE_TIME,LOCATION,IBAN_CODE,IP_ADDRESS,US_SSN,TAX,STOCK,ISIN_CODE,PROFIT"
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
    
    # Login lockout (brute-force mitigation)
    LOGIN_MAX_FAILED_ATTEMPTS: int = int(os.getenv("LOGIN_MAX_FAILED_ATTEMPTS", "3"))
    LOGIN_LOCKOUT_SECONDS: int = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "60"))

    # MFA / TOTP (Google Authenticator)
    MFA_PENDING_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("MFA_PENDING_TOKEN_EXPIRE_MINUTES", "10"))
    # Issuer label shown in the authenticator app (service name, not "Google Authenticator")
    TOTP_ISSUER: str = os.getenv("TOTP_ISSUER", os.getenv("APP_NAME", "Secure Data Protection System"))
    MFA_MAX_FAILED_ATTEMPTS: int = int(os.getenv("MFA_MAX_FAILED_ATTEMPTS", "5"))
    MFA_LOCKOUT_SECONDS: int = int(os.getenv("MFA_LOCKOUT_SECONDS", "300"))
    
    # Email inbox: max raw attachment bytes stored per file in log (MongoDB document limit)
    EMAIL_ATTACHMENT_MAX_STORE_BYTES: int = int(
        os.getenv("EMAIL_ATTACHMENT_MAX_STORE_BYTES", str(5 * 1024 * 1024))
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

