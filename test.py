import paho.mqtt.client as mqtt
import ssl
import time
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Broker configuration
broker_host = "mqtt.portabo.cz"
broker_port = 8883
client_id = "AttentID_test_client"
topic = "/rv-catcher/ble_devices"  # Changed from wildcard to specific topic
username = "rv-catcher"
password = "D6U5ERM7VAIdh7vaCa4fg6Leh"

# Define callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Connected to MQTT Broker at {broker_host}:{broker_port}")
        # Subscribe to topic
        client.subscribe(topic)
        logger.info(f"Subscribed to topic: {topic}")
    else:
        logger.error(f"Failed to connect to MQTT broker, return code {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        qos = msg.qos
        
        logger.info(f"Received message: {topic} (QoS: {qos})")
        logger.info(f"Payload: {payload}")
        
        # Try to parse JSON
        try:
            json_data = json.loads(payload)
            logger.info(f"Parsed JSON: {json_data}")
        except:
            logger.info("Payload is not valid JSON")
            
            # For BLE device data in non-JSON format, try to extract information
            if "mac" in payload:
                logger.info("Detected BLE device data, attempting to extract information")
                try:
                    # Try to find MAC address in the payload
                    if "'mac':" in payload:
                        mac_start = payload.find("'mac': '") + 8
                        if mac_start > 8:  # means we found the pattern
                            mac_end = payload.find("'", mac_start)
                            mac_address = payload[mac_start:mac_end]
                            logger.info(f"Extracted MAC address: {mac_address}")
                except Exception as extract_error:
                    logger.error(f"Error extracting information: {extract_error}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

# Create MQTT client
client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)

# Set auth credentials
client.username_pw_set(username, password)

# Set TLS
client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)

# Set callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect to broker
logger.info(f"Connecting to MQTT broker at {broker_host}:{broker_port}...")
client.connect(broker_host, broker_port)

# Start the loop
client.loop_start()

try:
    # Keep the script running
    logger.info("Listening for messages. Press Ctrl+C to exit.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Exiting...")
    client.loop_stop()
    client.disconnect()