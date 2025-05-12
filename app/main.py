from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import engine, Base, get_db
# Only import the essential routers for now
from app.api import mqtt
from app.mqtt import mqtt_client
from app.mqtt.handler import MQTTHandler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AttentID BLE Scanner API",
    description="API for collecting and processing BLE device data from AttentID scanners",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only the MQTT router for now
app.include_router(mqtt.router, prefix="/mqtt", tags=["MQTT"])

# MQTT client setup and connection
mqtt_handler = None

@app.on_event("startup")
async def startup_event():
    global mqtt_handler
    
    # Get database session
    db = next(get_db())
    
    # Create MQTT handler
    mqtt_handler = MQTTHandler(db)
    
    # Define message handler
    def handle_mqtt_message(topic, payload, qos):
        # Process MQTT message
        mqtt_handler.process_message(topic, payload, qos)
    
    # Register handler for the specific topic
    mqtt_client.register_handler("/rv-catcher/ble_devices", handle_mqtt_message)
    
    # Connect to MQTT broker
    connected = mqtt_client.connect()
    if connected:
        logger.info("MQTT client connected successfully")
    else:
        logger.error("Failed to connect MQTT client")

@app.on_event("shutdown")
async def shutdown_event():
    # Disconnect MQTT client
    mqtt_client.disconnect()
    logger.info("Application shutdown complete")

@app.get("/")
def root():
    return {
        "message": "Welcome to the AttentID BLE Scanner API",
        "documentation": "/docs",
        "endpoints": {
            "mqtt": {
                "receive": "/mqtt/receive",
                "messages": "/mqtt/messages"
            }
        }
    }