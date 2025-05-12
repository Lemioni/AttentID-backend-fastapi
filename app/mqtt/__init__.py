from paho.mqtt import client as mqtt_client
import logging
from app.core.database import settings
from typing import Callable, Dict
import random
import ssl
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self):
        self.client_id = f"{settings.MQTT_CLIENT_ID}_{random.randint(0, 1000)}"
        self.broker = settings.MQTT_BROKER_HOST
        self.port = settings.MQTT_BROKER_PORT
        self.topic = settings.MQTT_TOPIC
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD
        self.use_tls = settings.MQTT_USE_TLS
        
        # Update client initialization with callback_api_version
        self.client = mqtt_client.Client(client_id=self.client_id, callback_api_version=mqtt_client.CallbackAPIVersion.VERSION1)
        
        # Set auth credentials if provided
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # Set TLS if enabled
        if self.use_tls:
            self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
        
        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.message_handlers: Dict[str, Callable[[str, str, int], None]] = {}
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT Broker at {self.broker}:{self.port}")
            
            # Subscribe ONLY to the specific topic
            specific_topic = "/rv-catcher/ble_devices"
            self.client.subscribe(specific_topic)
            logger.info(f"Subscribed to topic: {specific_topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        qos = msg.qos
        
        logger.info(f"Received message: {topic} (QoS: {qos})")
        
        # Process message using registered handlers
        found_handler = False
        for pattern, handler in self.message_handlers.items():
            import re
            if pattern == topic:  # Direct match first
                found_handler = True
                try:
                    handler(topic, payload, qos)
                    logger.info(f"Successfully processed message with handler")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                break
                
        if not found_handler:
            logger.warning(f"No handler found for topic {topic}")

    def connect(self):
        # Simple connect implementation
        try:
            self.client.connect(self.broker, self.port)
            self.client.loop_start()
            time.sleep(1)  # Give time to connect
            return self.connected
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self):
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT broker")

    def register_handler(self, topic_pattern: str, handler: Callable[[str, str, int], None]):
        """Register a handler function for a specific topic pattern"""
        self.message_handlers[topic_pattern] = handler
        logger.info(f"Handler registered for topic pattern: {topic_pattern}")

mqtt_client = MQTTClient()