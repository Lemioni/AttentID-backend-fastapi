"""
Modul pro zpracování MQTT zpráv a jejich ukládání do databáze.
Obsahuje logiku pro parsování různých formátů zpráv a jejich persistenci.
"""

import json
import logging
import re
from sqlalchemy.orm import Session
from app.models.models import Device, Topic, MQTTEntry, User
from app.schemas.schemas import MQTTMessage
from datetime import datetime
from typing import Any, Dict, List, Optional

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
            
            # Inicializace device_id jako None
            device_id = None
            
            # Nejprve zkusíme parsovat jako JSON
            try:
                payload_data = json.loads(payload)
                logger.info(f"Parsovaný JSON payload: {payload_data}")
                
                # Pokud payload obsahuje device_id, použijeme ho
                if isinstance(payload_data, dict) and 'device_id' in payload_data:
                    device_id = payload_data['device_id']
                    logger.info(f"Použit device_id z payloadu: {device_id}")
            except json.JSONDecodeError:
                logger.warning(f"Payload není validní JSON: {payload}")
                
                # Zpracování Python dictionary formátu z BLE scanneru
                if "'mac':" in payload or "'data':" in payload:
                    logger.info("Detekována BLE data zařízení, pokus o extrakci informací")
                    
                    # Převod Python dict stringu na JSON string
                    try:
                        # Nahrazení jednoduchých uvozovek dvojitými pro JSON kompatibilitu
                        fixed_payload = payload.replace("'", '"')
                        # Pokus o parsování upraveného payloadu
                        try:
                            json_data = json.loads(fixed_payload)
                            logger.info("Úspěšný převod Python dict na JSON")
                            
                            # Extrakce MAC adresy
                            if 'data' in json_data and 'mac' in json_data['data']:
                                device_id = json_data['data']['mac']
                                logger.info(f"Extrahována MAC adresa: {device_id}")
                        except json.JSONDecodeError:
                            # Pokud to nefunguje, použijeme regex pro extrakci MAC
                            mac_match = re.search(r"'mac':\s*'([0-9A-F:]+)'", payload, re.IGNORECASE)
                            if mac_match:
                                device_id = mac_match.group(1)
                                logger.info(f"Extrahována MAC adresa pomocí regex: {device_id}")
                    except Exception as e:
                        logger.error(f"Chyba při extrakci informací: {e}")
            
            # Vytvoření objektu zprávy
            message = MQTTMessage(
                topic=topic,
                payload=payload,
                qos=qos,
                device_id=device_id
            )
            
            # Uložení zprávy do databáze
            self._save_to_database(message)
            
            logger.info(f"Úspěšně zpracována zpráva z tématu: {topic}")
            
        except Exception as e:
            logger.error(f"Chyba při zpracování MQTT zprávy: {e}", exc_info=True)
    
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
            
            logger.info(f"Použit systémový uživatel s ID: {system_user.id_users}")
            
            # Získání nebo vytvoření tématu
            topic_obj = self.db.query(Topic).filter(Topic.topic == message.topic).first()
            if not topic_obj:
                logger.info(f"Vytváření nového tématu: {message.topic}")
                topic_obj = Topic(
                    topic=message.topic,
                    id_users_created=system_user.id_users,
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
                        id_users=system_user.id_users
                    )
                    self.db.add(device)
                    self.db.commit()
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