import pika
import json
import time
import requests
import os
import sys


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")
API_BASE_URL = os.getenv("API_BASE_URL", "http://api-service:5000")
API_FAKE_URL = f"{API_BASE_URL}/evento/random"

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.exchange_declare(exchange='gym_events', exchange_type='direct')

def init_users(max_retries=10, retry_delay=5):
    print("[Producer] Intentando inicializar usuarios...")
    for attempt in range(max_retries):
        try:
            init_response = requests.post(f"{API_BASE_URL}/inicializar", json={"cantidad": 100})
            if init_response.status_code == 200:
                print("[Producer] Usuarios inicializados correctamente")
                return True
            print(f"[Producer] Error al inicializar usuarios (intento {attempt+1}/{max_retries})")
            time.sleep(retry_delay)
        except Exception as e:
            print(f"[Producer] Error de conexión (intento {attempt+1}/{max_retries}): {e}")
            time.sleep(retry_delay)
    return False

# Reemplazar la inicialización existente con esto:
if not init_users():
    print("[Producer] No se pudo inicializar los usuarios después de varios intentos. Saliendo...")
    sys.exit(1)
    
    
# Bucle principal para generar eventos
while True:
    try:
        response = requests.get(API_FAKE_URL)
        if response.status_code == 200:
            event = response.json()
            routing_key = event.get("evento", "otro")
            channel.basic_publish(
                exchange='gym_events',
                routing_key=routing_key,
                body=json.dumps(event)
            )
            print(f"[Producer] Evento enviado: {event}")
        else:
            print(f"[Producer] Error al consultar la API: {response.status_code}")
    except Exception as e:
        print(f"[Producer] Error: {e}")
    time.sleep(3)