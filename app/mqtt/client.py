"""
MQTT klient pro připojení k MQTT brokeru a správu zpráv.
Poskytuje rozhraní pro připojení, odpojení a zpracování MQTT komunikace.
"""

import paho.mqtt.client as mqtt
from typing import Callable, Optional, Dict
import logging
from dataclasses import dataclass
import ssl
import time
import random

logger = logging.getLogger(__name__)

@dataclass
class MQTTMessage:
    """
    Datová třída reprezentující MQTT zprávu.
    Obsahuje téma, obsah zprávy a úroveň QoS.
    """
    topic: str  # Téma zprávy
    payload: bytes  # Obsah zprávy
    qos: int  # Quality of Service úroveň

class MQTTClient:
    """
    MQTT klient pro komunikaci s MQTT brokerem.
    Zajišťuje bezpečné připojení, správu zpráv a jejich zpracování.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: str = "",
        use_tls: bool = False,
        keepalive: int = 60,
        max_reconnect_delay: int = 300
    ):
        """
        Inicializace MQTT klienta.
        
        Parametry:
            host: Adresa MQTT brokeru
            port: Port MQTT brokeru
            username: Uživatelské jméno pro autentizaci (volitelné)
            password: Heslo pro autentizaci (volitelné)
            client_id: Identifikátor klienta
            use_tls: Použít TLS šifrování
            keepalive: Interval pro keep-alive zprávy v sekundách
            max_reconnect_delay: Maximální interval mezi pokusy o připojení v sekundách
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.use_tls = use_tls
        self.keepalive = keepalive
        self.max_reconnect_delay = max_reconnect_delay
        self.reconnect_delay = 1  # Počáteční interval pro reconnect
        self.handlers: Dict[str, Callable] = {}
        self._setup_client()
    
    def _setup_client(self) -> None:
        """
        Nastavení MQTT klienta včetně přihlašovacích údajů a callback funkcí.
        Konfiguruje TLS pokud je požadováno.
        """
        # Přidání random čísla k client_id pro unikátnost
        unique_client_id = f"{self.client_id}_{random.randint(0, 1000)}"
        logger.info(f"Initializing MQTT client with ID: {unique_client_id}")
        logger.info(f"Broker: {self.host}:{self.port}, Username: {self.username}, Use TLS: {self.use_tls}")
        self.client = mqtt.Client(client_id=unique_client_id)
        
        if self.username and self.password:
            logger.info("Setting MQTT username and password.")
            self.client.username_pw_set(self.username, self.password)
        
        if self.use_tls:
            logger.info("Configuring TLS: cert_reqs=ssl.CERT_NONE, tls_insecure_set=True")
            self.client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.client.tls_insecure_set(True)
        
        # Nastavení keep-alive intervalu
        logger.info(f"Setting keepalive to {self.keepalive} seconds.")
        self.client.keepalive = self.keepalive
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Automatické opětovné připojení
        logger.info(f"Setting reconnect delay: min=1s, max={self.max_reconnect_delay}s.")
        self.client.reconnect_delay_set(min_delay=1, max_delay=self.max_reconnect_delay)
    
    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback funkce volaná při připojení k brokeru.
        Při úspěšném připojení znovu přihlásí odběr všech témat.
        """
        if rc == 0:
            logger.info(f"Successfully connected to MQTT broker with result code {rc}")
            self.reconnect_delay = 1  # Reset reconnect delay
            # Obnovení odběru všech témat
            if not self.handlers:
                logger.warning("No handlers registered. Not subscribing to any topics yet.")
            for topic in self.handlers.keys():
                logger.info(f"Subscribing to topic: {topic}")
                self.client.subscribe(topic)
        else:
            logger.error(f"Failed to connect to MQTT broker, result code: {rc}")
            self._handle_connection_failure()
    
    def _on_message(self, client, userdata, msg):
        """
        Callback funkce pro zpracování příchozích zpráv.
        Předá zprávu příslušnému handleru podle tématu.
        """
        logger.info(f"Received message on topic '{msg.topic}' with QoS {msg.qos}. Payload: {msg.payload[:100]}...") # Log first 100 bytes
        
        found_handler = False
        for sub_topic, handler_func in self.handlers.items():
            if mqtt.topic_matches_sub(sub_topic, msg.topic):
                try:
                    logger.debug(f"Calling handler registered for '{sub_topic}' with actual topic '{msg.topic}'")
                    handler_func(msg.topic, msg.payload, msg.qos)
                    found_handler = True
                    break # Assuming one message topic won't match multiple wildcard handlers in a way that requires all to run
                except Exception as e:
                    logger.error(f"Error processing MQTT message in registered handler for subscription '{sub_topic}' (actual topic '{msg.topic}'): {e}", exc_info=True)
                    # Decide if we should break or continue if one handler fails. For now, break.
                    found_handler = True # It was found, even if it errored
                    break
        
        if not found_handler:
            logger.warning(f"No handler's subscription pattern matched topic: {msg.topic}. Message ignored.")
    
    def _on_disconnect(self, client, userdata, rc):
        """
        Callback funkce volaná při odpojení od brokeru.
        Implementuje exponenciální backoff pro opětovné připojení.
        """
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker. Result code: {rc}. Attempting to reconnect.")
            self._handle_connection_failure() # This will be handled by paho-mqtt's auto-reconnect
        else:
            logger.info("Gracefully disconnected from MQTT broker.")
    
    def _handle_connection_failure(self):
        """
        Zpracování selhání připojení s exponenciálním backoff.
        """
        # Exponenciální backoff s náhodným jitterem
        jitter = random.uniform(0, 0.1) * self.reconnect_delay
        delay = min(self.reconnect_delay + jitter, self.max_reconnect_delay)
        logger.info(f"Čekání {delay:.1f} sekund před dalším pokusem o připojení")
        time.sleep(delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    def connect(self) -> bool:
        """
        Připojení k MQTT brokeru s automatickým opakováním.
        
        Vrací:
            bool: True pokud se připojení podařilo, jinak False
        """
        try:
            logger.info(f"Attempting to connect to MQTT broker at {self.host}:{self.port}...")
            self.client.connect(self.host, self.port, self.keepalive)
            self.client.loop_start()
            logger.info("MQTT client loop started.")
            # Connection success/failure is handled by _on_connect callback
            return True # Indicates attempt was made, actual status via callback
        except Exception as e:
            logger.error(f"Exception during initial connect call to {self.host}:{self.port}: {e}", exc_info=True)
            # self._handle_connection_failure() # paho-mqtt auto-reconnect should handle this
            return False
    
    def disconnect(self) -> None:
        """
        Odpojení od MQTT brokeru.
        Zastaví smyčku zpracování zpráv a odpojí klienta.
        """
        self.client.loop_stop()
        self.client.disconnect()
    
    def register_handler(self, topic: str, handler: Callable) -> None:
        """
        Registrace handleru pro zpracování zpráv z daného tématu.
        
        Parametry:
            topic: Téma pro odběr
            handler: Callback funkce pro zpracování zpráv
        """
        logger.info(f"Registering handler for topic: {topic}")
        self.handlers[topic] = handler
        if self.client.is_connected():
            logger.info(f"Client is connected. Subscribing to new topic: {topic}")
            self.client.subscribe(topic)
        else:
            logger.info(f"Client not connected. Subscription to {topic} will occur upon connection.")
    
    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        """
        Publikování zprávy do zadaného tématu.
        
        Parametry:
            topic: Téma pro publikaci
            payload: Obsah zprávy
            qos: Quality of Service úroveň (výchozí 0)
        """
        try:
            self.client.publish(topic, payload, qos)
        except Exception as e:
            logger.error(f"Nepodařilo se publikovat zprávu: {e}") 