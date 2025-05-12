import json
import logging
import re
from sqlalchemy.orm import Session
from app.models.models import Device, Topic, MQTTEntry, User
from app.schemas.schemas import MQTTMessage
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTHandler:
    def __init__(self, db: Session):
        self.db = db
    
    def process_message(self, topic: str, payload: str, qos: int):
        """
        Process an MQTT message and store it in the database
        
        Args:
            topic: The MQTT topic
            payload: The message payload
            qos: Quality of Service level
        """
        try:
            logger.info(f"Processing message from topic: {topic}")
            
            # Initialize device_id as None
            device_id = None
            
            # First try to parse as JSON
            try:
                payload_data = json.loads(payload)
                logger.info(f"Parsed JSON payload: {payload_data}")
                
                # If payload contains a device_id field, use that
                if isinstance(payload_data, dict) and 'device_id' in payload_data:
                    device_id = payload_data['device_id']
                    logger.info(f"Using device_id from payload: {device_id}")
            except json.JSONDecodeError:
                logger.warning(f"Payload is not valid JSON: {payload}")
                
                # Handle the Python dictionary-like format from BLE scanner
                if "'mac':" in payload or "'data':" in payload:
                    logger.info("Detected BLE device data, attempting to extract information")
                    
                    # Convert Python dict string to JSON string
                    try:
                        # Replace single quotes with double quotes for JSON compatibility
                        fixed_payload = payload.replace("'", '"')
                        # Try parsing the fixed payload
                        try:
                            json_data = json.loads(fixed_payload)
                            logger.info("Successfully converted Python dict to JSON")
                            
                            # Extract MAC address
                            if 'data' in json_data and 'mac' in json_data['data']:
                                device_id = json_data['data']['mac']
                                logger.info(f"Extracted MAC address: {device_id}")
                        except json.JSONDecodeError:
                            # If that doesn't work, use regex to extract the MAC
                            import re
                            mac_match = re.search(r"'mac':\s*'([0-9A-F:]+)'", payload, re.IGNORECASE)
                            if mac_match:
                                device_id = mac_match.group(1)
                                logger.info(f"Extracted MAC address using regex: {device_id}")
                    except Exception as e:
                        logger.error(f"Error extracting information: {e}")
            
            # Create message object
            message = MQTTMessage(
                topic=topic,
                payload=payload,
                qos=qos,
                device_id=device_id
            )
            
            # Save message to database
            self._save_to_database(message)
            
            logger.info(f"Successfully processed message from topic: {topic}")
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    def _save_to_database(self, message: MQTTMessage):
        """
        Save MQTT message to the database
        
        Args:
            message: The MQTT message object
        """
        try:
            logger.info(f"Starting save_to_database for message with topic: {message.topic}")
            
            # Get or create a system user (required for foreign keys)
            system_user = self.db.query(User).filter(User.email == "system@attentid.com").first()
            if not system_user:
                logger.info("Creating system user")
                system_user = User(
                    email="system@attentid.com",
                    created=datetime.now(),
                    active=datetime.now()
                )
                self.db.add(system_user)
                self.db.commit()
                self.db.refresh(system_user)
            
            logger.info(f"Using system user with ID: {system_user.id_users}")
            
            # Get or create topic
            topic_obj = self.db.query(Topic).filter(Topic.topic == message.topic).first()
            if not topic_obj:
                logger.info(f"Creating new topic: {message.topic}")
                topic_obj = Topic(
                    topic=message.topic,
                    id_users_created=system_user.id_users,
                    when_created=datetime.now()
                )
                self.db.add(topic_obj)
                self.db.commit()
                self.db.refresh(topic_obj)
            
            # Get or create device if device_id is provided
            device = None
            if message.device_id:
                device = self.db.query(Device).filter(Device.identification == message.device_id).first()
                
                if not device:
                    logger.info(f"Creating new device with ID: {message.device_id}")
                    device = Device(
                        description=f"Auto-created device {message.device_id}",
                        identification=message.device_id,
                        id_users=system_user.id_users
                    )
                    self.db.add(device)
                    self.db.commit()
                    self.db.refresh(device)
            
            # Create MQTT entry
            logger.info(f"Saving MQTT message to database")
            mqtt_entry = MQTTEntry(
                topic=message.topic,
                payload=message.payload,
                id_topics=topic_obj.id_topics,
                time=datetime.now()
            )
            self.db.add(mqtt_entry)
            self.db.commit()
            
            logger.info(f"Successfully saved MQTT message to database: Topic {topic_obj.topic}")
            if device:
                logger.info(f"Device: {device.identification}")
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving to database: {e}", exc_info=True)
            raise

def send_to_mqtt(topic: str, payload: Any):
    """
    Send data to MQTT broker with the required format
    
    Args:
        topic: MQTT topic (without prefix)
        payload: Data to be sent
    
    Returns:
        True if successful, False otherwise
    """
    from app.mqtt import mqtt_client
    
    # Convert payload to string if it's not already
    if not isinstance(payload, str):
        if isinstance(payload, dict) or isinstance(payload, list):
            payload = json.dumps(payload)
        else:
            payload = str(payload)
    
    # Send to broker
    return mqtt_client.publish(topic, payload)