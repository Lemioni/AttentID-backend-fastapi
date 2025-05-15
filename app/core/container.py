from dependency_injector import containers, providers
from sqlalchemy.orm import Session

from app.core.database import Database, SessionLocal
from app.mqtt.handler import MQTTHandler
from app.mqtt.client import MQTTClient
from app.config.settings import Settings, get_settings

class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Singleton(get_settings)
    
    # Database
    database = providers.Singleton(Database, db_url=config.provided.DATABASE_URL)
    
    # Session Factory - provides a new session each time it's called
    session = providers.Factory(SessionLocal)
    
    # MQTT Client
    mqtt_client = providers.Singleton(
        MQTTClient,
        host=config.provided.MQTT_BROKER_HOST,
        port=config.provided.MQTT_BROKER_PORT,
        username=config.provided.MQTT_USERNAME,
        password=config.provided.MQTT_PASSWORD,
        client_id=config.provided.MQTT_CLIENT_ID,
        use_tls=config.provided.MQTT_USE_TLS,
        keepalive=60,  # 60 second keepalive interval
        max_reconnect_delay=300  # 5 minute maximum reconnection delay
    )
    
    # MQTT Handler
    mqtt_handler = providers.Singleton(
        MQTTHandler,
        db=session,
    )

# Create a global container instance
container = Container() 
# Dependency utility function
def get_db_session() -> Session:
    db = container.session() # Call the factory
    try:
        yield db
    finally:
        db.close()