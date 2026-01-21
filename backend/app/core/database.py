"""
Database connection and session management
Handles connection pooling and session lifecycle
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create engine with connection pooling
# Using QueuePool for better performance under concurrent load
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,  # number of connections to maintain
    max_overflow=20,  # additional connections under high load
    pool_pre_ping=True,  # verify connections before using
    pool_recycle=3600,  # recycle connections after 1 hour
    echo=settings.ENVIRONMENT == "development",  # log SQL in dev
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    Event listener for new database connections
    Good place to set connection-level settings
    """
    logger.info("New database connection established")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get database sessions
    Ensures sessions are properly closed after request
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # use db here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions in scripts/workers
    
    Usage:
        with get_db_context() as db:
            # use db here
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database - create tables if they don't exist
    In production, use Alembic migrations instead
    """
    from app.models.database import Base
    
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def check_db_connection() -> bool:
    """
    Health check for database connectivity
    Returns True if connection is healthy
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False