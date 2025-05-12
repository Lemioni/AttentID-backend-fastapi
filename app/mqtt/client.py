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
        self.client = mqtt.Client(client_id=unique_client_id)
        
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        if self.use_tls:
            self.client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.client.tls_insecure_set(True)
        
        # Nastavení keep-alive intervalu
        self.client.keepalive = self.keepalive
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Automatické opětovné připojení
        self.client.reconnect_delay_set(min_delay=1, max_delay=self.max_reconnect_delay)
    
    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback funkce volaná při připojení k brokeru.
        Při úspěšném připojení znovu přihlásí odběr všech témat.
        """
        if rc == 0:
            logger.info("Připojeno k MQTT brokeru")
            self.reconnect_delay = 1  # Reset reconnect delay
            # Obnovení odběru všech témat
            for topic in self.handlers.keys():
                self.client.subscribe(topic)
        else:
            logger.error(f"Nepodařilo se připojit k MQTT brokeru, kód: {rc}")
            self._handle_connection_failure()
    
    def _on_message(self, client, userdata, msg):
        """
        Callback funkce pro zpracování příchozích zpráv.
        Předá zprávu příslušnému handleru podle tématu.
        """
        if msg.topic in self.handlers:
            try:
                self.handlers[msg.topic](msg.topic, msg.payload, msg.qos)
            except Exception as e:
                logger.error(f"Chyba při zpracování MQTT zprávy: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """
        Callback funkce volaná při odpojení od brokeru.
        Implementuje exponenciální backoff pro opětovné připojení.
        """
        if rc != 0:
            logger.warning("Neočekávané odpojení od MQTT brokeru")
            self._handle_connection_failure()
    
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
            self.client.connect(self.host, self.port)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Nepodařilo se připojit k MQTT brokeru: {e}")
            self._handle_connection_failure()
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
        self.handlers[topic] = handler
        if self.client.is_connected():
            self.client.subscribe(topic)
    
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