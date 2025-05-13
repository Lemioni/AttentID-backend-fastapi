"""
Hlavní MQTT service modul, který se stará o životní cyklus MQTT klienta a zpracování zpráv.
"""

import asyncio
import logging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.mqtt.client import MQTTClient
from app.mqtt.handler import MQTTHandler
from app.config.settings import settings

# Konfigurace logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTService:
    """
    MQTT Service třída, která spravuje MQTT připojení a zpracování zpráv.
    Zajišťuje kompletní životní cyklus MQTT klienta včetně připojení k brokeru,
    zpracování zpráv a odpojení.
    """
    
    def __init__(self):
        """
        Inicializace MQTT služby s připojením k databázi a handlerem zpráv.
        Vytvoří instanci MQTT klienta a nastaví zpracování příchozích zpráv.
        """
        # Vytvoření databázové session
        self.db = SessionLocal()
        
        # Vytvoření MQTT handleru pro zpracování zpráv
        self.mqtt_handler = MQTTHandler(self.db)
        
        # Vytvoření MQTT klienta s konfigurací z nastavení aplikace
        self.mqtt_client = MQTTClient(
            host=settings.MQTT_BROKER_HOST,
            port=settings.MQTT_BROKER_PORT,
            username=settings.MQTT_USERNAME,
            password=settings.MQTT_PASSWORD,
            client_id=settings.MQTT_CLIENT_ID,
            use_tls=settings.MQTT_USE_TLS
        )
        
        # Registrace handleru zpráv pro nakonfigurované téma
        self.mqtt_client.register_handler(
            settings.MQTT_TOPIC,
            self.mqtt_handler.process_message
        )
    
    async def start(self):
        """
        Spuštění MQTT služby a udržování připojení.
        Pokusí se připojit k MQTT brokeru a v případě úspěchu
        udržuje připojení aktivní pomocí periodických kontrol.
        """
        logger.info("Spouštění MQTT služby...")
        
        if self.mqtt_client.connect():
            logger.info("Úspěšně připojeno k MQTT brokeru")
            
            # Udržování služby v běhu s periodickými kontrolami
            while True:
                await asyncio.sleep(1)
        else:
            logger.error("Nepodařilo se připojit k MQTT brokeru")
    
    async def stop(self):
        """
        Zastavení MQTT služby a vyčištění připojení.
        Bezpečně ukončí připojení k MQTT brokeru a uzavře databázovou session.
        """
        logger.info("Zastavování MQTT služby...")
        self.mqtt_client.disconnect()
        self.db.close()

async def main():
    """
    Hlavní vstupní bod pro samostatné spuštění MQTT služby.
    Vytvoří instanci služby a spustí ji s obsluhou přerušení.
    """
    service = MQTTService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Přijat signál pro vypnutí")
    finally:
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main()) 