#!/usr/bin/env python3
"""
🌱 AgroPapin Edge App - Versión Simple
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



if __name__ == "__main__":
    main()