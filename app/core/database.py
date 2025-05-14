from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from typing import Generator

from app.config.settings import settings

Base = declarative_base()

class Database:
    def __init__(self, db_url: str):
        self.engine = create_engine(
            db_url,
            pool_pre_ping=True,  # Enable connection pool "pre-ping" feature
            pool_size=5,         # Set a reasonable pool size
            max_overflow=10      # Maximum number of connections to overflow
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_database(self) -> None:
        """Create all database tables. Drops the users table first for development."""
        # WARNING: This will delete all data in the 'users' table on each startup.
        # Not suitable for production. Use Alembic for production migrations.
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Generator:
        """Provide a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    @property
    def get_engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        return self.engine

# Create a global database instance
database = Database(settings.DATABASE_URL)
SessionLocal = database.SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()