import pika
import json
import time
import requests
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")
API_FAKE_URL = os.getenv("API_FAKE_URL", "http://api_falsa:5000/evento/random")

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.exchange_declare(exchange='gym_events', exchange_type='direct')

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
            print("[Producer] Error al consultar la API")
    except Exception as e:
        print(f"[Producer] Error: {e}")
    time.sleep(3)