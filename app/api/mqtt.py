from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.models import MQTTEntry
from app.schemas.schemas import MQTTMessage
from app.mqtt.handler import MQTTHandler
import json

router = APIRouter()

@router.post("/receive", status_code=status.HTTP_202_ACCEPTED)
async def receive_mqtt_message(
    message: MQTTMessage,
    db: Session = Depends(get_db)
):
    """
    Endpoint to manually receive MQTT messages (for testing or direct API calls)
    """
    handler = MQTTHandler(db)
    handler.process_message(message.topic, message.payload, message.qos)
    return {"status": "Message received"}

@router.get("/messages", response_model=List[Dict[str, Any]])
def get_mqtt_messages(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get MQTT messages
    """
    messages = db.query(MQTTEntry).order_by(MQTTEntry.time.desc()).offset(skip).limit(limit).all()
    
    result = []
    for msg in messages:
        entry = {
            "id": msg.id_mqttenteries,
            "topic": msg.topic,
            "payload": msg.payload,
            "time": msg.time.isoformat() if msg.time else None,
            "processed": msg.processed
        }
        
        result.append(entry)
        
    return result