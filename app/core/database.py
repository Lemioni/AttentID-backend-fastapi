from sqlalchemy import create_engine, text
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
        with self.engine.connect() as connection:
            # Drop the materialized view first, if it exists
            connection.execute(text("DROP MATERIALIZED VIEW IF EXISTS newest_device_enteries CASCADE;"))
            # Commit the transaction for the DROP MATERIALIZED VIEW
            connection.commit()
            
        # Now proceed to drop all tables defined in Base.metadata
        # Base.metadata.drop_all(bind=self.engine) # Commented out to prevent dropping tables on startup
        Base.metadata.create_all(bind=self.engine) # Creates tables if they don't exist

        # Create the materialized view
        with self.engine.connect() as connection:
            create_mv_sql = """
            CREATE MATERIALIZED VIEW newest_device_enteries AS
            WITH ParsedTopics AS (
                SELECT
                    id_mqttenteries,
                    time,
                    topic,
                    payload,
                    split_part(topic, '/', 4) AS raspberry_uuid, -- Assumes topic like /rv-catcher/ble_devices/RASP_UUID/MAC_ADDR
                    split_part(topic, '/', 5) AS found_mac_address
                FROM
                    mqttenteries
                WHERE
                    topic LIKE '/rv-catcher/ble_devices/%/%' -- Filters for relevant topics
            ),
            RankedEnteries AS (
                SELECT
                    id_mqttenteries,
                    time,
                    topic,
                    payload,
                    raspberry_uuid,
                    found_mac_address,
                    ROW_NUMBER() OVER (PARTITION BY raspberry_uuid, found_mac_address ORDER BY time DESC) as rn
                FROM
                    ParsedTopics
                WHERE
                    raspberry_uuid IS NOT NULL AND raspberry_uuid <> '' AND -- Ensures raspberry_uuid is valid
                    found_mac_address IS NOT NULL AND found_mac_address <> '' -- Ensures found_mac_address is valid
            )
            SELECT
                id_mqttenteries,
                time,
                raspberry_uuid,
                found_mac_address
            FROM
                RankedEnteries
            WHERE
                rn = 1; -- Selects the newest entry for each pair
            """
            connection.execute(text(create_mv_sql))
            connection.commit()
    
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