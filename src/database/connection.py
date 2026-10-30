"""
Database connection and session management

Supports both SQLite (development) and PostgreSQL (production) via environment variable.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from .models import Base

# Import auth models to ensure they're registered with Base
# This must be done before init_db() is called
try:
    from src.auth.models import User, APIKey
except ImportError:
    # Auth models not yet available during initial setup
    pass

# Database configuration from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./eaglevision_anpr.db"  # Default to SQLite for development
)

# SQLite-specific configuration (for development/testing)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
else:
    # PostgreSQL configuration (for production)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10,
        echo=False
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency for FastAPI endpoints.
    
    Yields database session and ensures cleanup.
    
    Usage:
        @app.get("/videos/")
        def get_videos(db: Session = Depends(get_db)):
            return db.query(Video).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    
    Safe to call multiple times - only creates missing tables.
    
    Usage:
        from src.database import init_db
        init_db()
    """
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized: {DATABASE_URL}")
    print(f"✅ Tables: {', '.join(Base.metadata.tables.keys())}")


def drop_all_tables():
    """
    Drop all tables from database.
    
    ⚠️ WARNING: This deletes ALL data!
    Only use for testing or resetting the database.
    """
    Base.metadata.drop_all(bind=engine)
    print(f"⚠️  All tables dropped from: {DATABASE_URL}")


def get_database_url():
    """Return the current database URL (sanitized)"""
    # Hide password in URL if present
    url = DATABASE_URL
    if "@" in url and "://" in url:
        parts = url.split("://")
        if len(parts) == 2:
            scheme = parts[0]
            rest = parts[1]
            if "@" in rest:
                credentials, host_db = rest.split("@", 1)
                if ":" in credentials:
                    user = credentials.split(":")[0]
                    url = f"{scheme}://{user}:***@{host_db}"
    return url
