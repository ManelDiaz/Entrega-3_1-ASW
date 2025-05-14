import pika
import json
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.queue_declare(queue='gym_events')

def callback(ch, method, properties, body):
    event = json.loads(body)
    # Ejemplo de alerta: más de 10 unidades (si el evento tiene 'unidades')
    if event.get("unidades", 0) > 10:
        print(f"[Alert] Pedido especial: {event}")
    # Alerta para eventos de gimnasio (puedes personalizar)
    elif event.get("evento") == "entrada" and event.get("zona") == "Cardio":
        print(f"[Alert] Entrada en zona Cardio: {event}")
    else:
        print(f"[Alert] Evento normal: {event}")

channel.basic_consume(queue='gym_events', on_message_callback=callback, auto_ack=True)
print("[Alert] Esperando eventos...")
channel.start_consuming()