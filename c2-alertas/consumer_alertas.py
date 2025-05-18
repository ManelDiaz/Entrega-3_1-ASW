import pika
import json
import os
from pymongo import MongoClient
from datetime import datetime

print("[DEBUG] Iniciando script...")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq-service")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")

# Capacidades máximas específicas por zona
ZONE_CAPACITY = {
    "Cardio": 20,
    "Pesas": 20,
    "Piscina": 15,
    "Yoga": 10
}

print(f"[DEBUG] Config: RABBITMQ_HOST={RABBITMQ_HOST}")
print(f"[DEBUG] Config: MONGO_URI={MONGO_URI}")

try:
    print("[DEBUG] Conectando a MongoDB...")
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['gym']
    collection = db['events']
    alerts_collection = db['alerts']  # Nueva colección separada para alertas
    print("[DEBUG] Conexión a MongoDB establecida")
except Exception as e:
    print(f"[ERROR] Error conectando a MongoDB: {e}")
    raise e


try:
    print("[DEBUG] Conectando a RabbitMQ...")
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue='gym_events')
    print("[DEBUG] Conexión a RabbitMQ establecida")
except Exception as e:
    print(f"[ERROR] Error conectando a RabbitMQ: {e}")
    raise e

def callback(ch, method, properties, body):
    event = json.loads(body)
    current_time = datetime.utcnow()
    
    # Generar alerta de ocupación si es entrada
    if event.get("evento") == "entrada":
        # Contar usuarios en la zona
        zona = event.get("zona")
        if zona:
            usuarios_en_zona = collection.count_documents({
                "evento": "entrada",
                "zona": zona
            }) - collection.count_documents({
                "evento": "salida",
                "zona": zona
            })
            
            # Obtener capacidad específica para la zona
            capacidad_zona = ZONE_CAPACITY.get(zona)
            
            # Si hay más de 80% de ocupación para esta zona específica
            if usuarios_en_zona > (capacidad_zona * 0.8):
                alerta = {
                    "tipo": "ocupacion",
                    "zona": zona,
                    "porcentaje": (usuarios_en_zona / capacidad_zona) * 100,
                    "timestamp": current_time
                }
                alerts_collection.insert_one(alerta)  # Insertar en la colección de alertas
    
    # Alertas de tiempo excesivo
    if event.get("evento") == "entrada":
        alerts_collection.insert_one({  # Insertar en la colección de alertas
            "tipo": "usuario",
            "id_usuario": event.get("usuario_id"),
            "zona": event.get("zona"),
            "tiempo_sesion": 121,
            "timestamp": current_time
        })

print("[Alert] Esperando eventos...")
channel.basic_consume(queue='gym_events', on_message_callback=callback, auto_ack=True)
channel.start_consuming()