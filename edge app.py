import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import threading
import telemetry_aggregator as ta

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
global DEVICE_ID
DEVICE_ID = "n/a"
MQTT_SERVER = "agro-papin-001"

# Topics MQTT
TOPIC_STATUS = f"{MQTT_SERVER}/status"
TOPIC_COMMANDS = f"{MQTT_SERVER}/commands"
TOPIC_TELEMETRY = f"{MQTT_SERVER}/telemetry"
TOPIC_IRRIGATION = "command/irrigation/d1ff4b71-1cd0-4fc0-b0d2-d4e5b5825fba"

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
        client.subscribe(TOPIC_IRRIGATION)
        log(f"Suscrito a: {TOPIC_STATUS}")
        log(f"Suscrito a: {TOPIC_TELEMETRY}")
        log(f"Suscrito a: {TOPIC_IRRIGATION}")
        
    else:
        log(f"Error conectando al MQTT: {rc}", "ERROR")

def handle_irrigation_command(duration_minutes):
    """Inicia y detiene el riego por un tiempo determinado."""
    try:
        duration_seconds = duration_minutes * 60
        log(f"Iniciando riego automático por {duration_minutes} minutos.")
        
        # 1. Enviar comando para iniciar riego
        send_command("irrigate")
        
        # 2. Esperar el tiempo especificado
        time.sleep(duration_seconds)
        
        # 3. Enviar comando para detener riego
        send_command("stop")
        log(f"Riego detenido automáticamente después de {duration_minutes} minutos.")
        
    except Exception as e:
        log(f"Error durante el riego automático: {e}", "ERROR")

def on_message(client, userdata, msg):
    global device_data
    global DEVICE_ID
    
    try:
        topic = msg.topic
        
        #log(f"Mensaje de {topic}: {msg.payload.decode()}")
        
        # Actualizar datos del dispositivo
        if topic == TOPIC_STATUS:
            data = json.loads(msg.payload.decode())
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
            data = json.loads(msg.payload.decode())
            # Actualizar datos visibles
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

            # Enviar muestra al agregador simple (conteo por muestras)
            try:
                ts = device_data.get("timestamp") or int(time.time())
                sample = {
                    "device_id": data.get("device_id", DEVICE_ID),
                    "plot_id": "d31cc3bc-df79-4926-af6d-49555ab893be",
                    "timestamp": int(ts),
                    "humidity": ta._safe_float(device_data.get("humidity")),
                    "temperature": ta._safe_float(device_data.get("temperature")),
                    "soilMoisture": ta._safe_float(device_data.get("soil_moisture")),
                }
                ta.add_sample(sample)
            except Exception as e:
                log(f"Error procesando y agregando muestra: {e}", "ERROR")
        elif topic == TOPIC_IRRIGATION:
            log(f"Mensaje de riego recibido: {data}")
            try:
                # 1. Decodificar el payload de bytes a string (ej: b'2' -> '2')
                payload_str = msg.payload.decode()
                
                # 2. Convertir el string a un número entero (ej: '2' -> 2)
                duration_minutes = int(payload_str)
                
                log(f"Comando de riego recibido por {duration_minutes} minutos.")
                
                # 3. Ejecutar el riego en un hilo para no bloquear la aplicación
                irrigation_thread = threading.Thread(target=handle_irrigation_command, args=(duration_minutes,))
                irrigation_thread.start()

            except ValueError:
                log(f"Error: El payload de riego '{msg.payload.decode()}' no es un número válido.", "ERROR")
            except Exception as e:
                log(f"Error al procesar comando de riego: {e}", "ERROR")
            
            # Salimos de la función on_message para no intentar procesar esto como JSON más abajo
            return


    except Exception as e:
        log(f"Error procesando mensaje: {e}", "ERROR")

def send_command(action):
    """Enviar comando al ESP32"""
    try:
        command = {
            "action": action,
            "timestamp": int(time.time() * 1000),
            "source": "python-edge-app"
        }
        
        client.publish(TOPIC_COMMANDS, json.dumps(command))
        log(f"Comando enviado: {action.upper()}")
        
    except Exception as e:
        log(f"Error enviando comando: {e}", "ERROR")

def show_device_status():
    global DEVICE_ID
    """Mostrar estado actual del dispositivo"""
    print("\n" + "="*50)
    print("📱 ESTADO DEL DISPOSITIVO AGROPAPIN")
    print("="*50)
    print(f"Dispositivo: {device_data.get('device_id', DEVICE_ID)}")
    print(f"Online: {'✅ SÍ' if device_data['status'] else '❌ NO'}")
    print(f"Riego: {'🟢 ACTIVO' if device_data['relay_state'] else '🔴 INACTIVO'}")
    
    if device_data['last_seen']:
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