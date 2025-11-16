#!/usr/bin/env python3
"""
AgroPapin Edge App - Versión Simple
Conecta con ESP32 via MQTT para control de riego
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import threading

MQTT_BROKER = "192.168.100.7"
MQTT_PORT = 1883
DEVICE_ID = "agro-papin-001"

# Topics MQTT
TOPIC_STATUS = f"agropapin/devices/{DEVICE_ID}/status"
TOPIC_COMMANDS = f"agropapin/devices/{DEVICE_ID}/commands"
TOPIC_TELEMETRY = f"agropapin/devices/{DEVICE_ID}/telemetry"

# Variables globales
device_data = {
    "online": False,
    "relay_state": False,
    "led_state": False,
    "soil_moisture": 0.0,
    "wifi_rssi": 0,
    "last_seen": None
}

def log(message, level="INFO"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def on_connect(client, userdata, flags, rc):
    """Callback cuando se conecta al broker MQTT"""
    if rc == 0:
        log("Conectado al broker MQTT")
        
        # Suscribirse a topics del ESP32
        client.subscribe(TOPIC_STATUS)
        client.subscribe(TOPIC_TELEMETRY)
        log(f"Suscrito a: {TOPIC_STATUS}")
        log(f"Suscrito a: {TOPIC_TELEMETRY}")
        
    else:
        log(f"Error conectando al MQTT: {rc}", "ERROR")



if __name__ == "__main__":
    main()