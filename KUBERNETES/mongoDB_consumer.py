import pika, json
from pymongo import MongoClient

mongo_client = MongoClient('mongodb://mongodb:27017/')
db = mongo_client['gym']             
collection = db['events']             

def callback(ch, method, properties, body):
    event = json.loads(body)
    collection.insert_one(event)
    print(f"[Storage] Evento guardado en MongoDB: {event}")

credentials = pika.PlainCredentials('user', 'bitnami')
parameters = pika.ConnectionParameters('rabbitmq', 5672, '/', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.queue_declare(queue='gym_events')  # Usamos la cola 'gym_events'
channel.basic_consume(queue='gym_events', on_message_callback=callback, auto_ack=True)
print("[Storage] Esperando eventos...")
channel.start_consuming()
