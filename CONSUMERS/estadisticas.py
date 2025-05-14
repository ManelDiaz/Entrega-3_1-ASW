import pika
import json
import os
import time
from collections import Counter
from threading import Thread

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.queue_declare(queue='gym_events')

event_counter = Counter()
zone_counter = Counter()
active_users = set()

def print_stats():
    while True:
        time.sleep(10)
        print("\n--- Estadísticas últimas 10s ---")
        print(f"Eventos por tipo: {dict(event_counter)}")
        print(f"Check-ins por zona: {dict(zone_counter)}")
        print(f"Usuarios activos: {len(active_users)}")
        print("-------------------------------\n")
        event_counter.clear()
        zone_counter.clear()

def callback(ch, method, properties, body):
    event = json.loads(body)
    tipo = event.get("evento", "otro")
    event_counter[tipo] += 1

    if tipo == "entrada":
        zona = event.get("zona", "desconocida")
        zone_counter[zona] += 1
        active_users.add(event.get("usuario_id"))
    elif tipo == "salida":
        active_users.discard(event.get("usuario_id"))

Thread(target=print_stats, daemon=True).start()
print("[Stats] Esperando eventos...")
channel.basic_consume(queue='gym_events', on_message_callback=callback, auto_ack=True)
channel.start_consuming()