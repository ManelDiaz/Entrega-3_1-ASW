import pika
import json
from pymongo import MongoClient
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client['gym']
collection = db['events']

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# Declarar el exchange
channel.exchange_declare(exchange='gym_events', exchange_type='direct')

# Declarar una cola exclusiva para este consumidor
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

# Vincular la cola al exchange con las claves de enrutamiento que necesites
routing_keys = ['entrada', 'salida', 'uso_maquina', 'otro']  # Ajusta según los tipos de eventos que esperas
for key in routing_keys:
    channel.queue_bind(exchange='gym_events', queue=queue_name, routing_key=key)

def callback(ch, method, properties, body):
    event = json.loads(body)
    collection.insert_one(event)
    print(f"[Storage] Evento guardado en MongoDB: {event}")

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
print("[Storage] Esperando eventos...")
channel.start_consuming()