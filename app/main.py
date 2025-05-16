import sys
print(f"--- Python Executable: {sys.executable}")
print(f"--- Python Path: {sys.path}")
"""
Hlavní modul aplikace.
Inicializuje FastAPI aplikaci, databázi a MQTT klienta.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.container import container
from app.config.settings import settings
from app.routes import mqtt, database, auth, users, devices, statistics, certificates # Added statistics and certificates
from app.services.auth import create_default_roles, create_default_admin_user # Import both functions

# Konfigurace logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """
    Vytvoření a konfigurace FastAPI aplikace.
    Nastavuje CORS, routery a dependency injection.
    
    Vrací:
        FastAPI: Nakonfigurovaná FastAPI aplikace
    """
    # Vytvoření FastAPI instance
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="API for collecting and processing BLE device data from AttentID scanners",
        version="1.0.0"
    )
    
    # Nastavení CORS
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Připojení API routeru
    application.include_router(mqtt.router, prefix=settings.API_V1_STR)
    application.include_router(database.router, prefix=settings.API_V1_STR)
    application.include_router(auth.router) # No prefix for /api/auth
    application.include_router(users.router) # Prefix /api/users is defined in users.py
    application.include_router(devices.router, prefix=settings.API_V1_STR)
    application.include_router(statistics.router, prefix=settings.API_V1_STR) # Added statistics router

    application.include_router(certificates.router, prefix=settings.API_V1_STR) # Added certificates router

    return application

app = create_application()

@app.on_event("startup")
async def startup_event():
    """
    Událost spuštění aplikace.
    Inicializuje databázi a MQTT klienta.
    """
    # Inicializace databáze
    container.database().create_database() # This likely creates tables

    # Create default roles and admin user after tables are created
    # We need a database session here.
    # Get a new session from the factory provided by the container.
    db = container.session()
    try:
        # First create default roles
        create_default_roles(db)
        
        # Then create default admin user
        create_default_admin_user(db)
    finally:
        db.close()
    
    # Inicializace MQTT klienta
    # mqtt_client = container.mqtt_client()
    # mqtt_handler = container.mqtt_handler()
    
    # Registrace MQTT handleru zpráv
    # mqtt_client.register_handler(
    #     settings.MQTT_TOPIC,
    #     mqtt_handler.process_message
    # )
    
    # Připojení k MQTT brokeru
    # if mqtt_client.connect():
    #     logger.info("MQTT klient úspěšně připojen")
    # else:
    #     logger.error("Nepodařilo se připojit MQTT klienta")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Událost vypnutí aplikace.
    Odpojí MQTT klienta a vyčistí prostředky.
    """
    # Odpojení MQTT klienta
    # container.mqtt_client().disconnect()
    logger.info("Aplikace úspěšně ukončena")

@app.get("/")
def root():
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME}",
        "documentation": "/docs",
        "version": "1.0.0",
        "endpoints": {
            "mqtt": {
                "base": f"{settings.API_V1_STR}/mqtt",
                "receive": f"{settings.API_V1_STR}/mqtt/receive",
                "messages": f"{settings.API_V1_STR}/mqtt/messages"
            },
            "database": {
                "base": f"{settings.API_V1_STR}/database",
                "status": f"{settings.API_V1_STR}/database/status",
                "populate": f"{settings.API_V1_STR}/database/populate-all"
            },
            "auth": {
                "base": "/api/auth",
                "register": "/api/auth/register"
            }
        }
    }