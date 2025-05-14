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

channel.queue_declare(queue='gym_events')

def callback(ch, method, properties, body):
    event = json.loads(body)
    collection.insert_one(event)
    print(f"[Storage] Evento guardado en MongoDB: {event}")

channel.basic_consume(queue='gym_events', on_message_callback=callback, auto_ack=True)
print("[Storage] Esperando eventos...")
channel.start_consuming()