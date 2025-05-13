from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db
from app.models.models import MQTTEntry
from app.schemas.schemas import MQTTMessage
from app.mqtt.handler import MQTTHandler

class MQTTService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.handler = MQTTHandler(db)
    
    async def process_message(self, message: MQTTMessage) -> None:
        """Process an incoming MQTT message"""
        self.handler.process_message(message.topic, message.payload, message.qos)
    
    def get_messages(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get paginated MQTT messages"""
        messages = (
            self.db.query(MQTTEntry)
            .order_by(MQTTEntry.time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return [
            {
                "id": msg.id_mqttenteries,
                "topic": msg.topic,
                "payload": msg.payload,
                "time": msg.time.isoformat() if msg.time else None,
                "processed": msg.processed
            }
            for msg in messages
        ] 