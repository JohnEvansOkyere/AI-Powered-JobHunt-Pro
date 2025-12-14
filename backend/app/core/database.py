"""
Database Configuration

Simple SQLAlchemy setup for PostgreSQL database connection and session management.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from urllib.parse import urlparse, urlunparse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _try_connection_pooler_fallback(db_url: str) -> str:
    """
    Automatically convert direct Supabase connection to Connection Pooler
    to avoid IPv6 connectivity issues.
    """
    if ":5432" not in db_url or "supabase.co" not in db_url or "pooler" in db_url:
        return db_url
    
    try:
        parsed = urlparse(db_url)
        hostname = parsed.hostname
        
        if not hostname or not hostname.startswith("db."):
            return db_url
        
        # Extract project reference
        project_ref = hostname.replace("db.", "").replace(".supabase.co", "")
        
        # Common Supabase regions - try them in order
        regions = ["us-east-1", "us-west-1", "eu-west-1", "ap-southeast-1", "ap-northeast-1"]
        
        logger.info(f"Attempting to auto-convert direct connection to Session Mode Pooler...")
        
        # Try Session Mode first (port 5432, username: postgres.[PROJECT-REF])
        # According to Supabase docs: https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler
        for region in regions:
            try:
                pooler_hostname = f"aws-0-{region}.pooler.supabase.com"
                new_username = f"postgres.{project_ref}"  # Session mode uses postgres.[PROJECT-REF]
                new_netloc = f"{new_username}:{parsed.password}@{pooler_hostname}:5432"  # Session mode uses port 5432
                new_path = parsed.path or "/postgres"
                
                test_url = urlunparse(parsed._replace(
                    netloc=new_netloc,
                    path=new_path
                ))
                
                # Quick connection test
                test_engine = create_engine(
                    test_url,
                    pool_pre_ping=False,
                    connect_args={"connect_timeout": 3, "sslmode": "require"}
                )
                with test_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                logger.info(f"✅ Successfully auto-converted to Session Mode Pooler: {pooler_hostname}:5432")
                return test_url
            except Exception:
                continue
        
        logger.warning("Could not auto-detect Connection Pooler region. Please get the correct URL from Supabase Dashboard.")
        return db_url
    except Exception as e:
        logger.warning(f"Error in Connection Pooler fallback: {e}")
        return db_url


# Create database engine with automatic Connection Pooler fallback
db_url = settings.DATABASE_URL

# Auto-convert direct connection to pooler if needed
if ":5432" in db_url and "supabase.co" in db_url:
    db_url = _try_connection_pooler_fallback(db_url)

engine = create_engine(
    db_url,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    connect_args={
        "connect_timeout": 10,
        "sslmode": "require" if "pooler" in db_url else "prefer",
    },
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        Session: SQLAlchemy database session
        
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

