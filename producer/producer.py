import pika
import json
import time
import requests
import os
import sys
import random

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")
API_BASE_URL = os.getenv("API_BASE_URL", "http://api-service:5000")
API_ENTRADA_URL = f"{API_BASE_URL}/evento/entrada"
API_SALIDA_URL = f"{API_BASE_URL}/evento/salida"

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.exchange_declare(exchange='gym_events', exchange_type='direct')

# Estado interno del producer
usuarios_totales = 100  # Número total de usuarios inicializados
usuarios_dentro = 0     # Contador de usuarios dentro del gimnasio

def init_users(max_retries=10, retry_delay=5):
    print("[Producer] Intentando inicializar usuarios...")
    for attempt in range(max_retries):
        try:
            init_response = requests.post(f"{API_BASE_URL}/inicializar", json={"cantidad": usuarios_totales})
            if init_response.status_code == 200:
                print("[Producer] Usuarios inicializados correctamente")
                return True
            print(f"[Producer] Error al inicializar usuarios (intento {attempt+1}/{max_retries})")
            time.sleep(retry_delay)
        except Exception as e:
            print(f"[Producer] Error de conexión (intento {attempt+1}/{max_retries}): {e}")
            time.sleep(retry_delay)
    return False

# Inicializar usuarios
if not init_users():
    print("[Producer] No se pudo inicializar los usuarios después de varios intentos. Saliendo...")
    sys.exit(1)

# Bucle principal para generar eventos
while True:
    try:
        # Decidir si generar un evento de entrada o salida
        if usuarios_dentro < usuarios_totales and (usuarios_dentro == 0 or random.random() < 0.7):
            # Generar un evento de entrada (70% de probabilidad si hay usuarios fuera)
            response = requests.get(API_ENTRADA_URL)
        elif usuarios_dentro > 0:
            # Generar un evento de salida
            response = requests.get(API_SALIDA_URL)
        else:
            print("[Producer] No hay usuarios disponibles para generar eventos")
            time.sleep(3)
            continue

        # Procesar la respuesta de la API
        if response.status_code == 200:
            event = response.json()
            routing_key = event.get("evento", "otro")
            channel.basic_publish(
                exchange='gym_events',
                routing_key=routing_key,
                body=json.dumps(event)
            )
            print(f"[Producer] Evento enviado: {event}")

            # Actualizar el estado interno
            if event["evento"] == "entrada":
                usuarios_dentro += 1
            elif event["evento"] == "salida":
                usuarios_dentro -= 1
        else:
            print(f"[Producer] Error al consultar la API: {response.status_code}")

    except Exception as e:
        print(f"[Producer] Error: {e}")

    # Esperar antes de generar el siguiente evento
    time.sleep(3)