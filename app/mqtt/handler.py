"""
Modul pro zpracování MQTT zpráv a jejich ukládání do databáze.
Obsahuje logiku pro parsování různých formátů zpráv a jejich persistenci.
"""

import json
import logging
import re
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.models import Device, Topic, MQTTEntry, User
from app.schemas.schemas import MQTTMessage
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.models.models import Certificate

# Konfigurace logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTHandler:
    """
    Handler pro zpracování MQTT zpráv.
    Zajišťuje parsování zpráv a jejich ukládání do databáze.
    """
    
    def __init__(self, db: Session):
        """
        Inicializace handleru s databázovou session.
        
        Parametry:
            db: SQLAlchemy databázová session
        """
        self.db = db
    
    def process_message(self, topic: str, payload: str, qos: int):
        """
        Zpracování MQTT zprávy a její uložení do databáze.
        Podporuje různé formáty zpráv včetně JSON a BLE dat.
        
        Parametry:
            topic: MQTT téma zprávy
            payload: Obsah zprávy
            qos: Quality of Service úroveň
        """
        try:
            logger.info(f"Zpracování zprávy z tématu: {topic}")

            # Decode payload from bytes to string (assuming UTF-8)
            if isinstance(payload, bytes):
                payload_str = payload.decode('utf-8')
            else:
                payload_str = payload # Already a string

            # Replace single quotes with double quotes for JSON compatibility
            payload_for_json = payload_str.replace("'", '"')
            
            # Inicializace device_id jako None
            device_id = None
            
            # Nejprve zkusíme parsovat jako JSON
            try:
                payload_data = json.loads(payload_for_json)
                logger.info(f"Parsovaný JSON payload: {payload_data}")
                
                # Pokud payload obsahuje device_id, použijeme ho
                if isinstance(payload_data, dict) and 'device_id' in payload_data:
                    device_id = payload_data['device_id']
                    logger.info(f"Použit device_id z payloadu: {device_id}")
            except json.JSONDecodeError:
                logger.warning(f"Payload není validní JSON: {payload_str}")
                
                # Zpracování Python dictionary formátu z BLE scanneru
                # Use the decoded string for this check
                if "'mac':" in payload_str or "'data':" in payload_str:
                    logger.info("Detekována BLE data zařízení, pokus o extrakci informací")
                    
                    # Převod Python dict stringu na JSON string
                    # The payload_for_json already has single quotes replaced
                    try:
                        # Pokus o parsování upraveného payloadu
                        try:
                            json_data = json.loads(payload_for_json) # Use payload_for_json which has quotes replaced
                            logger.info("Úspěšný převod Python dict na JSON")
                            
                            # Extrakce MAC adresy
                            if 'data' in json_data and 'mac' in json_data['data']:
                                device_id = json_data['data']['mac']
                                logger.info(f"Extrahována MAC adresa: {device_id}")
                        except json.JSONDecodeError:
                            # Pokud to nefunguje, použijeme regex pro extrakci MAC
                            # Use payload_str for regex as it's the original string content
                            mac_match = re.search(r"'mac':\s*'([0-9A-F:]+)'", payload_str, re.IGNORECASE)
                            if mac_match:
                                device_id = mac_match.group(1)
                                logger.info(f"Extrahována MAC adresa pomocí regex: {device_id}")
                    except Exception as e:
                        logger.error(f"Chyba při extrakci informací: {e}")
            
            # Vytvoření objektu zprávy
            # Ensure MQTTMessage stores the decoded string representation
            message = MQTTMessage(
                topic=topic,
                payload=payload_str, # Store the decoded string
                qos=qos,
                device_id=device_id
            )
            
            # Uložení zprávy do databáze
            self._save_to_database(message)

            # Add debugging log
            logger.info(f"Checking topic for presence verification: {topic}")
            
            # Check if this is a user presence verification message
            if "overenaadresa" in topic or "overenaadresa_uzivatele" in topic:
                logger.info(f"Found presence verification topic: {topic}")
                self._handle_presence_verification(topic, payload_str)
            
            
            logger.info(f"Úspěšně zpracována zpráva z tématu: {topic}")
            
        except Exception as e:
            logger.error(f"Chyba při zpracování MQTT zprávy: {e}", exc_info=True)

    def _handle_presence_verification(self, topic: str, payload: str):
        """
        Handle user presence verification message and create certificate automatically.
        Extracts user and raspberry IDs from the topic and creates attendance certificates.
        
        Args:
            topic: MQTT topic containing presence verification
            payload: Message payload
        """
        try:
            logger.info(f"Processing presence verification for topic: {topic}")
            
            # Extract user_id and raspberry_uuid from topic
            parts = topic.split('/')
            user_id = None
            raspberry_uuid = None
            
            # Find user ID (last part after "overenaadresa_uzivatele")
            if len(parts) >= 2 and parts[-2] == "overenaadresa_uzivatele":
                user_id = parts[-1]
                logger.info(f"Extracted user ID: {user_id}")
            else:
                # Try alternative patterns
                for i, part in enumerate(parts):
                    if part == "overenaadresa" and i+1 < len(parts):
                        user_id = parts[i+1]
                        logger.info(f"Extracted user ID from alternative pattern: {user_id}")
                        break
            
            # Find Raspberry UUID (typically third component in our pattern)
            for part in parts:
                if len(part) > 30 and '-' in part:
                    raspberry_uuid = part
                    logger.info(f"Extracted Raspberry UUID: {raspberry_uuid}")
                    break
            
            # If we couldn't find a UUID that looks like a raspberry UUID, try the third component
            if not raspberry_uuid and len(parts) > 3:
                raspberry_uuid = parts[3]
                logger.info(f"Using third path component as Raspberry UUID: {raspberry_uuid}")
            
            # If we found both IDs, create a certificate
            if user_id and raspberry_uuid:
                logger.info(f"Creating automatic certificate for user {user_id} at location {raspberry_uuid}")
                
                # Get a database session for certificate creation
                from app.core.database import SessionLocal
                from app.services.certificates import create_certificate
                from app.models.models import Certificate
                from datetime import datetime, timedelta
                
                db = SessionLocal()
                try:
                    # Check if a certificate already exists for this user at this location within the last hour
                    current_time = datetime.now()
                    time_threshold = current_time - timedelta(hours=1)
                    
                    existing_certificate = db.query(Certificate).filter(
                        Certificate.user_id == user_id,
                        Certificate.raspberry_uuid == raspberry_uuid,
                        Certificate.timestamp >= time_threshold
                    ).first()
                    
                    if existing_certificate:
                        logger.info(f"Certificate already exists for user {user_id} at location {raspberry_uuid} " 
                                f"created at {existing_certificate.timestamp}")
                        return
                    
                    # Parse additional data from payload if present
                    metadata = {}
                    try:
                        if isinstance(payload, str) and (payload.startswith('{') or payload.startswith("'")):
                            # Try to parse JSON or Python dict string
                            clean_payload = payload.replace("'", '"')
                            try:
                                payload_data = json.loads(clean_payload)
                                if isinstance(payload_data, dict):
                                    metadata = payload_data
                                    logger.info(f"Parsed payload metadata: {metadata}")
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse payload as JSON: {payload}")
                    except Exception as e:
                        logger.warning(f"Error parsing payload metadata: {str(e)}")
                    
                    # Create certificate
                    certificate = create_certificate(
                        db=db,
                        user_id=user_id,
                        raspberry_uuid=raspberry_uuid,
                        timestamp=current_time,
                        time_window_minutes=30  # Default window
                    )
                    
                    logger.info(f"Successfully created certificate: {certificate.id}")
                    
                    # Here you could add code to notify the user by email
                    try:
                        # Get user email if needed
                        user = db.query(User).filter(User.id == user_id).first()
                        if user and user.email:
                            logger.info(f"Would notify user {user.email} about new certificate {certificate.id}")
                            # Implement email notification here if needed
                    except Exception as e:
                        logger.warning(f"Could not prepare email notification: {str(e)}")
                    
                except HTTPException as he:
                    logger.warning(f"Could not create certificate: {he.detail}")
                except Exception as e:
                    logger.error(f"Error creating certificate: {str(e)}", exc_info=True)
                finally:
                    db.close()
            else:
                logger.warning(f"Could not extract both user_id and raspberry_uuid from topic: {topic}")
                if not user_id:
                    logger.warning("Missing user_id")
                if not raspberry_uuid:
                    logger.warning("Missing raspberry_uuid")
        
        except Exception as e:
            logger.error(f"Error handling presence verification: {str(e)}", exc_info=True)
    
    def _save_to_database(self, message: MQTTMessage):
        """
        Uložení MQTT zprávy do databáze.
        Vytváří nebo aktualizuje související záznamy (Topic, Device).
        
        Parametry:
            message: Objekt MQTT zprávy k uložení
        """
        try:
            logger.info(f"Začátek ukládání do databáze pro zprávu s tématem: {message.topic}")
            
            # Získání nebo vytvoření systémového uživatele (potřebné pro cizí klíče)
            system_user = self.db.query(User).filter(User.email == "system@attentid.com").first()
            if not system_user:
                logger.info("Vytváření systémového uživatele")
                system_user = User(
                    email="system@attentid.com",
                    created=datetime.now(),
                    active=datetime.now()
                )
                self.db.add(system_user)
                self.db.commit()
                self.db.refresh(system_user)
            
            logger.info(f"Použit systémový uživatel s ID: {system_user.id}")
            
            # Získání nebo vytvoření tématu
            # Získání nebo vytvoření tématu
            topic_obj = self.db.query(Topic).filter(Topic.topic == message.topic).first()
            if not topic_obj:
                logger.info(f"Vytváření nového tématu: {message.topic}")
                topic_obj = Topic(
                    topic=message.topic,
                    id_created_by=system_user.id,  # Changed from system_user.id_users
                    when_created=datetime.now()
                )
                self.db.add(topic_obj)
                self.db.commit()
                self.db.refresh(topic_obj)
            
            # Získání nebo vytvoření zařízení pokud je poskytnut device_id
            device = None
            if message.device_id:
                device = self.db.query(Device).filter(Device.identification == message.device_id).first()
                
                if not device:
                    logger.info(f"Vytváření nového zařízení s ID: {message.device_id}")
                    device = Device(
                        description=f"Automaticky vytvořené zařízení {message.device_id}",
                        identification=message.device_id,
                        id_user=system_user.id  # Changed from system_user.id_users
                    )
                    self.db.add(device)
                    self.db.commit()
                    self.db.refresh(device)
                    self.db.refresh(device)
            
            # Vytvoření MQTT záznamu
            logger.info(f"Ukládání MQTT zprávy do databáze")
            mqtt_entry = MQTTEntry(
                topic=message.topic,
                payload=message.payload,
                id_topics=topic_obj.id_topics,
                time=datetime.now()
            )
            self.db.add(mqtt_entry)
            self.db.commit()
            
            logger.info(f"Úspěšně uložena MQTT zpráva do databáze: Téma {topic_obj.topic}")
            if device:
                logger.info(f"Zařízení: {device.identification}")
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Chyba při ukládání do databáze: {e}", exc_info=True)
            raise

def send_to_mqtt(topic: str, payload: Any):
    """
    Odeslání dat do MQTT brokeru v požadovaném formátu.
    
    Parametry:
        topic: MQTT téma (bez prefixu)
        payload: Data k odeslání
    
    Vrací:
        bool: True pokud úspěšně odesláno, jinak False
    """
    from app.mqtt import mqtt_client
    
    # Převod payloadu na string pokud už není
    if not isinstance(payload, str):
        if isinstance(payload, dict) or isinstance(payload, list):
            payload = json.dumps(payload)
        else:
            payload = str(payload)
    
    # Odeslání na broker
    return mqtt_client.publish(topic, payload)