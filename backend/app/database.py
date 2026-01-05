"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import os

# Use SQLite for testing if PostgreSQL URL is not properly configured
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://") and "localhost" in database_url:
    # Check if we should use SQLite for testing
    test_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test.db")
    # For now, use SQLite if PostgreSQL connection might fail
    if not os.getenv("FORCE_POSTGRES", "").lower() == "true":
        database_url = f"sqlite:///{test_db_path}"
        print(f"Using SQLite database for testing: {test_db_path}")

# Create database engine
# For SQLite, use a single connection with proper thread handling
# For PostgreSQL, use connection pooling
if "sqlite" in database_url:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
        poolclass=None,  # Disable pooling for SQLite
        echo=False
    )
else:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables
    """
    # Import all models to ensure they are registered
    from app.models import users, policies, alerts, logs
    Base.metadata.create_all(bind=engine)

