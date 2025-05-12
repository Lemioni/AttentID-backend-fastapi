from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/raspberry_pi_data")
    mqtt_broker_host: str = os.getenv("MQTT_BROKER_HOST", "mqtt.portabo.cz")
    mqtt_broker_port: int = int(os.getenv("MQTT_BROKER_PORT", "8883"))
    mqtt_client_id: str = os.getenv("MQTT_CLIENT_ID", "RomanVaibarHailoCounter")
    mqtt_topic: str = os.getenv("MQTT_TOPIC", "/rv-catcher/ble_devices")  # Change to specific topic
    mqtt_username: str = os.getenv("MQTT_USERNAME", "rv-catcher")
    mqtt_password: str = os.getenv("MQTT_PASSWORD", "D6U5ERM7VAIdh7vaCa4fg6Leh")
    mqtt_use_tls: bool = os.getenv("MQTT_USE_TLS", "True").lower() == "true"

settings = Settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()