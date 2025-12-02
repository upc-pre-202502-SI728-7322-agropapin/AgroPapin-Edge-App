import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import threading
import telemetry_aggregator as ta

# --- Broker y Topics para Telemetría ---
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_SERVER = "agro-papin-001"
TOPIC_STATUS = f"{MQTT_SERVER}/status"
TOPIC_COMMANDS = f"{MQTT_SERVER}/commands"
TOPIC_TELEMETRY = f"{MQTT_SERVER}/telemetry"

# --- Broker y Topic para Riego ---
IRRIGATION_BROKER = "38.253.147.228" # O la IP de tu otro broker
TOPIC_IRRIGATION = "command/irrigation/d1ff4b71-1cd0-4fc0-b0d2-d4e5b5825fba"

# --- Variables Globales ---
global DEVICE_ID
DEVICE_ID = "n/a"
device_data = {
    "online": False,
    "relay_state": False,
    "led_state": False,
    "soil_moisture": 0.0,
    "wifi_rssi": 0,
    "last_seen": None
}
# Clientes MQTT globales para que send_command pueda acceder a ellos
client1 = None
client2 = None

def log(message, level="INFO"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

# --- Callbacks para Broker 1 (Telemetría y Estado) ---
def on_connect_broker1(client, userdata, flags, rc):
    """Callback cuando se conecta al broker MQTT principal"""
    if rc == 0:
        log("[Broker 1] Conectado al broker principal")
        client.subscribe(TOPIC_STATUS)
        client.subscribe(TOPIC_TELEMETRY)
        log(f"[Broker 1] Suscrito a: {TOPIC_STATUS}")
        log(f"[Broker 1] Suscrito a: {TOPIC_TELEMETRY}")
    else:
        log(f"[Broker 1] Error conectando: {rc}", "ERROR")

def on_message_broker1(client, userdata, msg):
    """Callback para mensajes del broker principal (JSON)"""
    global device_data
    global DEVICE_ID
    
    try:
        topic = msg.topic
        data = json.loads(msg.payload.decode())

        if topic == TOPIC_STATUS:
            device_data.update({
                "status": data.get("status", "offline"),
                "Irrigation": data.get("Irrigation", False),
                "relay_state": data.get("relay_state", False),
                "led_state": data.get("led_state", False),
                "wifi_rssi": data.get("wifi_rssi", 0),
                "last_seen": datetime.now()
            })
            DEVICE_ID = data.get("device_id", "n/a")
            
        elif topic == TOPIC_TELEMETRY:
            device_data["timestamp"] = data.get("timestamp")
            device_data["plot_id"] = "6bb0cf7a-a9b1-4878-8809-0eb74487cbe0"
            device_data["temperature"] = data.get("temperature")
            device_data["soil_moisture"] = data.get("soil_moisture")
            device_data["temperature_limit"] = data.get("temperature_limit")
            device_data["humidity_limit"] = data.get("humidity_limit")
            device_data["salinity"] = data.get("salinity")
            device_data["passed_temperature"] = data.get("passed_temperature")
            device_data["passed_humidity"] = data.get("passed_humidity")
            device_data["humidity"] = data.get("humidity")
            try:
                ts = device_data.get("timestamp") or int(time.time())
                sample = {
                    "device_id": data.get("device_id", DEVICE_ID),
                    "plot_id": "d31cc3bc-df79-4926-af6d-49555ab893be",
                    "timestamp": int(ts),
                    "humidity": ta._safe_float(data.get("humidity")),
                    "temperature": ta._safe_float(data.get("temperature")),
                    "soilMoisture": ta._safe_float(data.get("soil_moisture")),
                }
                ta.add_sample(sample)
            except Exception as e:
                log(f"Error procesando y agregando muestra: {e}", "ERROR")

    except json.JSONDecodeError:
        log(f"[Broker 1] Error: El mensaje en el tópico '{msg.topic}' no es un JSON válido: {msg.payload.decode()}", "ERROR")
    except Exception as e:
        log(f"[Broker 1] Error procesando mensaje: {e}", "ERROR")

# --- Callbacks para Broker 2 (Comandos de Riego) ---
def on_connect_broker2(client, userdata, flags, rc):
    """Callback cuando se conecta al broker de comandos de riego"""
    if rc == 0:
        log("[Broker 2] Conectado al broker de riego")
        client.subscribe(TOPIC_IRRIGATION)
        log(f"[Broker 2] Suscrito a: {TOPIC_IRRIGATION}")
    else:
        log(f"[Broker 2] Error conectando: {rc}", "ERROR")

def on_message_broker2(client, userdata, msg):
    """Callback para mensajes del broker de riego (Texto plano)"""
    try:
        duration_minutes = int(msg.payload.decode())
        log(f"Comando de riego recibido por {duration_minutes} minutos.")
        
        irrigation_thread = threading.Thread(target=handle_irrigation_command, args=(duration_minutes,))
        irrigation_thread.start()

    except ValueError:
        log(f"Error: El payload de riego '{msg.payload.decode()}' no es un número válido.", "ERROR")
    except Exception as e:
        log(f"Error al procesar comando de riego: {e}", "ERROR")

# --- Funciones de Comando y Lógica ---
def handle_irrigation_command(duration_minutes):
    """Inicia y detiene el riego por un tiempo determinado."""
    try:
        duration_seconds = duration_minutes * 60
        log(f"Iniciando riego automático por {duration_minutes} minutos.")
        send_command("irrigate")
        time.sleep(duration_seconds)
        send_command("stop")
        log(f"Riego detenido automáticamente después de {duration_minutes} minutos.")
    except Exception as e:
        log(f"Error durante el riego automático: {e}", "ERROR")

def send_command(action):
    """Enviar comando al ESP32 (a través del broker principal)"""
    global client1
    try:
        command = {
            "action": action,
            "timestamp": int(time.time() * 1000),
            "source": "python-edge-app"
        }
        if client1:
            client1.publish(TOPIC_COMMANDS, json.dumps(command))
            log(f"Comando enviado: {action.upper()}")
        else:
            log("Error: El cliente MQTT 1 no está conectado.", "ERROR")
    except Exception as e:
        log(f"Error enviando comando: {e}", "ERROR")

# --- Funciones de Interfaz de Usuario ---
def show_device_status():
    global DEVICE_ID
    """Mostrar estado actual del dispositivo"""
    print("\n" + "="*50)
    print("📱 ESTADO DEL DISPOSITIVO AGROPAPIN")
    print("="*50)
    print(f"Dispositivo: {device_data.get('device_id', DEVICE_ID)}")
    print(f"Online: {'✅ SÍ' if device_data.get('status') else '❌ NO'}")
    print(f"Riego: {'🟢 ACTIVO' if device_data.get('relay_state') else '🔴 INACTIVO'}")
    
    if device_data.get('last_seen'):
        print(f"Última vez visto: {device_data['last_seen'].strftime('%H:%M:%S')}")
    
    print("="*50)

def show_telemetry():
    global DEVICE_ID
    """Mostrar datos de telemetría"""
    print("\n" + "="*50)
    print("🌡️ TELEMETRÍA DEL DISPOSITIVO AGROPAPIN")
    print("="*50)
    print(f"Dispositivo: {device_data.get('device_id', DEVICE_ID)}")
    print(f"Timestamp: {device_data.get('timestamp', 'N/A')}")
    print(f"Temperatura: {device_data.get('temperature', 'N/A')} °C")
    print(f"Humedad del suelo: {device_data.get('humidity', 'N/A')} %")
    print(f"Límite de temperatura: {device_data.get('temperature_limit', 'N/A')} °C")
    print(f"Límite de humedad: {device_data.get('humidity_limit', 'N/A')} %")
    print(f"Salinidad: {device_data.get('salinity', 'N/A')} ppt")
    print(f"Superó límite de temperatura: {'SÍ' if device_data.get('passed_temperature') else 'NO'}")
    print(f"Superó límite de humedad: {'SÍ' if device_data.get('passed_humidity') else 'NO'}")
    print("="*50)

def interactive_menu():
    """Menú interactivo para controlar el dispositivo"""
    while True:
        print("\nCONTROLES AGROPAPIN:")
        print("1.Iniciar Riego")
        print("2.Detener Riego") 
        print("3.Ver Estado")
        print("4.Ver Telemetría")
        print("5.Salir")
        
        try:
            choice = input("\nSelecciona una opción (1-5): ").strip()
            
            if choice == "1":
                send_command("irrigate")
            elif choice == "2":
                send_command("stop")
            elif choice == "3":
                show_device_status()
            elif choice == "4":
                show_telemetry()
            elif choice == "5":
                log("Cerrando aplicación...")
                break
            else:
                print("Opción inválida")
                
        except KeyboardInterrupt:
            log("\nCerrando aplicación...")
            break
        except Exception as e:
            log(f"Error: {e}", "ERROR")

# --- Función Principal ---
def main():
    """Función principal que maneja ambas conexiones"""
    global client1, client2

    client1 = mqtt.Client(client_id="edge-app-main")
    client1.on_connect = on_connect_broker1
    client1.on_message = on_message_broker1

    client2 = mqtt.Client(client_id="edge-app-irrigation")
    client2.on_connect = on_connect_broker2
    client2.on_message = on_message_broker2
    
    log("Iniciando AgroPapin Edge App (Python)")
    
    try:
        log(f"Conectando a Broker 1 (Telemetría): {MQTT_BROKER}:{MQTT_PORT}")
        client1.connect(MQTT_BROKER, MQTT_PORT, 60)

        log(f"Conectando a Broker 2 (Riego): {IRRIGATION_BROKER}:{MQTT_PORT}")
        client2.connect(IRRIGATION_BROKER, MQTT_PORT, 60)
        
        client1.loop_start()
        client2.loop_start()
        
        interactive_menu()
        
    except Exception as e:
        log(f"Error fatal: {e}", "ERROR")
        
    finally:
        if client1:
            client1.loop_stop()
            client1.disconnect()
        if client2:
            client2.loop_stop()
            client2.disconnect()
        log("Ambas conexiones MQTT cerradas. Aplicación terminada.")

if __name__ == "__main__":
    main()
