"""
Modul definující MQTT endpointy API.
Poskytuje rozhraní pro manuální příjem MQTT zpráv a získávání historie.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.models import MQTTEntry
from app.schemas.schemas import MQTTMessage
from app.services.mqtt import MQTTService

# Vytvoření routeru pro MQTT endpointy
router = APIRouter(prefix="/mqtt", tags=["MQTT"])

@router.post("/receive", status_code=status.HTTP_202_ACCEPTED)
async def receive_mqtt_message(
    message: MQTTMessage,
    mqtt_service: MQTTService = Depends(),
):
    """
    Endpoint pro manuální příjem MQTT zpráv.
    Umožňuje testování nebo přímé API volání pro zpracování MQTT zpráv.
    
    Parametry:
        message: Příchozí MQTT zpráva k zpracování
        mqtt_service: Instance MQTT služby (injektováno)
    
    Vrací:
        dict: Potvrzení o přijetí zprávy
    """
    await mqtt_service.process_message(message)
    return {"status": "Zpráva přijata"}

@router.get("/messages", response_model=List[Dict[str, Any]])
def get_mqtt_messages(
    skip: int = 0, 
    limit: int = 100,
    mqtt_service: MQTTService = Depends(),
):
    """
    Get MQTT messages with pagination
    """
    return mqtt_service.get_messages(skip=skip, limit=limit) 