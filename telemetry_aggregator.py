import os
import requests
from datetime import datetime
import uuid
import time

# Configuración
BACKEND_ENDPOINT = os.getenv("BACKEND_ENDPOINT", "https://agropapin-backend.onrender.com/api/v1/telemetry/ingest-batch")
SAMPLES_LIMIT = 6
# Almacenamiento temporal
_buffer = []

def _safe_float(v):

    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def add_sample(sample):

    global _buffer
    _buffer.append(sample)
    
    print(f"Agregador: Muestra recibida ({len(_buffer)}/{SAMPLES_LIMIT})")

    if len(_buffer) >= SAMPLES_LIMIT:
        _process_and_send()

def _is_valid_uuid(val):
    if not val or not isinstance(val, str):
        return False
    try:
        uuid.UUID(val)
        return True
    except Exception:
        return False

def _process_and_send():
    global _buffer
    
    if not _buffer:
        return

    # 1. Calcular promedios de campos numéricos
    numeric_keys = set()
    for s in _buffer:
        for k, v in s.items():
            if isinstance(v, (int, float)) and k != "timestamp":
                numeric_keys.add(k)

    averages = {}
    for k in numeric_keys:
        values = [s[k] for s in _buffer if s.get(k) is not None]
        if values:
            averages[k] = sum(values) / len(values)

    # 2. Preparar payload
    # Usamos el device_id del primer sample y timestamps inicio/fin
    start_ts = min(s["timestamp"] for s in _buffer)
    end_ts = max(s["timestamp"] for s in _buffer)
    device_id = _buffer[0].get("device_id", "unknown")
    plot_id = _buffer[0].get("plot_id", "n/a")

    current_ts = int(time.time())

    # Construir objeto base, SOLO incluir plotId/serialNumber si son UUID válidos
    reading_resource = {
        "samples_count": len(_buffer),
        "timestamp": current_ts
    }

    if _is_valid_uuid(plot_id):
        reading_resource["plotId"] = plot_id
    else:
        print(f"Agregador: plotId inválido o ausente ('{plot_id}'), se omite del payload.")

    if _is_valid_uuid(device_id):
        reading_resource["serialNumber"] = device_id
    else:
        print(f"Agregador: device_id inválido o ausente ('{device_id}'), se omite del payload.")

    # aplanar: agregar promedios al objeto raíz
    reading_resource.update(averages)

    # el backend espera una lista de objetos
    payload = [reading_resource]

    print(f"Payload: {payload}")

    # 3. Enviar al endpoint
    try:
        print(f"Agregador: Enviando {len(_buffer)} muestras promediadas a {BACKEND_ENDPOINT}...")
        response = requests.post(BACKEND_ENDPOINT, json=payload, timeout=5)
        if 200 <= response.status_code < 300:
            print("Agregador: Envío exitoso.")
        else:
            print(f"Agregador: Error en envío. Status: {response.status_code}, Resp: {response.text}")
    except Exception as e:
        print(f"Agregador: Excepción al enviar: {e}")

    # 4. Vaciar lista
    _buffer = []
    print("Agregador: Buffer vaciado.")
