"""
Konfigurační modul aplikace.
Definuje všechna nastavení a konfigurační proměnné pro aplikaci.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import os

class Settings(BaseSettings):
    """
    Třída obsahující všechna nastavení aplikace.
    Používá pydantic pro validaci a načítání hodnot z prostředí.
    """
    
    # Database settings
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/attentid"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "raspberry_pi_data"
    
    # PgAdmin settings
    PGADMIN_DEFAULT_EMAIL: str = "admin@example.com"
    PGADMIN_DEFAULT_PASSWORD: str = "admin"
    
    # Blockchain settings
    CONTRACT_ADDRESS: str = "0xa8ab8223c92274c4644d8b40719fe577dc946ed3"
    ACCOUNT_PASSWORD: str = "pixmapixma"
    ACCOUNT_ADDRESS: str = "0x6fb64b24d6804970084a6b3a19a1d9e57182b06e"
    RPC_URL: str = "http://192.168.37.101:8545"
    
    # MQTT settings
    MQTT_BROKER_HOST: str = "mqtt.portabo.cz"
    MQTT_BROKER_PORT: int = 8883
    MQTT_CLIENT_ID: str = "raspberry_pi_mqtt"
    MQTT_TOPIC: str = "/rv-catcher/#"
    MQTT_USERNAME: str = "rv-catcher"
    MQTT_PASSWORD: str = "D6U5ERM7VAIdh7vaCa4fg6Leh"
    MQTT_USE_TLS: bool = True
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AttentID BLE Scanner API"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    # Logging settings
    LOG_LEVEL: str = "INFO"

    # JWT settings
    SECRET_KEY: str = "your_secret_key"  # Load from .env in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Admin user settings - can be overridden in .env file
    DEFAULT_ADMIN_EMAIL: str = "admin@attentid.com"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    DEFAULT_ADMIN_NAME: str = "System Administrator"
    
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache to avoid loading .env file on each call
    """
    return Settings()

# Create a global settings instance
settings = get_settings() 