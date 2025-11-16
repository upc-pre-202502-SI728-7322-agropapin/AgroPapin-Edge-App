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

def on_message(client, userdata, msg):
    """Callback cuando llega un mensaje MQTT"""
    global device_data
    
    try:
        topic = msg.topic
        data = json.loads(msg.payload.decode())
        
        log(f"Mensaje de {topic}: {msg.payload.decode()}")
        
        # Actualizar datos del dispositivo
        if topic == TOPIC_STATUS:
            device_data.update({
                "online": True,
                "relay_state": data.get("relay_state", False),
                "led_state": data.get("led_state", False),
                "wifi_rssi": data.get("wifi_rssi", 0),
                "last_seen": datetime.now()
            })
            
        elif topic == TOPIC_TELEMETRY:
            device_data["soil_moisture"] = data.get("soil_moisture", 0.0)
            
        # Mostrar estado actual
        show_device_status()
        
    except Exception as e:
        log(f"Error procesando mensaje: {e}", "ERROR")

def send_command(action, soil_moisture=25.0):
    """Enviar comando al ESP32"""
    try:
        command = {
            "action": action,
            "soil_moisture": soil_moisture,
            "timestamp": int(time.time() * 1000),
            "source": "python-edge-app"
        }
        
        client.publish(TOPIC_COMMANDS, json.dumps(command))
        log(f"Comando enviado: {action.upper()}")
        
    except Exception as e:
        log(f"Error enviando comando: {e}", "ERROR")

def show_device_status():
    """Mostrar estado actual del dispositivo"""
    print("\n" + "="*50)
    print("📱 ESTADO DEL DISPOSITIVO AGROPAPIN")
    print("="*50)
    print(f"Online: {'SÍ' if device_data['online'] else '❌ NO'}")
    print(f"Riego: {'ACTIVO' if device_data['relay_state'] else '🔴 INACTIVO'}")
    print(f"LED: {'ON' if device_data['led_state'] else '⚫ OFF'}")
    print(f"Humedad: {device_data['soil_moisture']:.1f}%")
    print(f"WiFi: {device_data['wifi_rssi']} dBm")
    
    if device_data['last_seen']:
        print(f"Última vez visto: {device_data['last_seen'].strftime('%H:%M:%S')}")
    
    print("="*50)

def interactive_menu():
    """Menú interactivo para controlar el dispositivo"""
    while True:
        print("\nCONTROLES AGROPAPIN:")
        print("1.Iniciar Riego")
        print("2.Detener Riego") 
        print("3.Ver Estado")
        print("4.Salir")
        
        try:
            choice = input("\nSelecciona una opción (1-4): ").strip()
            
            if choice == "1":
                moisture = input("Humedad del suelo (default 20%): ").strip()
                moisture = float(moisture) if moisture else 20.0
                send_command("irrigate", moisture)
                
            elif choice == "2":
                send_command("stop", 50.0)
                
            elif choice == "3":
                show_device_status()
                
            elif choice == "4":
                log("Cerrando aplicación...")
                break
                
            else:
                print("Opción inválida")
                
        except KeyboardInterrupt:
            log("\nCerrando aplicación...")
            break
        except Exception as e:
            log(f"Error: {e}", "ERROR")

def main():
    """Función principal"""
    global client
    
    log("Iniciando AgroPapin Edge App (Python)")
    log(f"Conectando a MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    
    # Configurar cliente MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # Conectar al broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Iniciar loop de MQTT en hilo separado
        client.loop_start()
        
        # Esperar un poco para establecer conexión
        time.sleep(2)
        
        # Iniciar menú interactivo
        interactive_menu()
        
    except Exception as e:
        log(f"Error fatal: {e}", "ERROR")
        
    finally:
        client.loop_stop()
        client.disconnect()
        log("Aplicación terminada")

if __name__ == "__main__":
    main()