import os
import requests
from datetime import datetime

# Configuración
BACKEND_ENDPOINT = os.getenv("BACKEND_ENDPOINT", "http://localhost:8000/api/telemetry")
SAMPLES_LIMIT = 10

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

    payload = {
        "device_id": device_id,
        "samples_count": len(_buffer),
        "start_ts": start_ts,
        "end_ts": end_ts,
        "averages": averages
    }

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
