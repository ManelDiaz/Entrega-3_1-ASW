import pika
import json
import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import time
from threading import Thread

print("[DEBUG] Iniciando script...")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq-service")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")

TIMEZONE_OFFSET = 2 
TIMEZONE_ESP = timezone(timedelta(hours=TIMEZONE_OFFSET))

def get_local_time():
    """Devuelve la hora actual en la zona horaria española"""
    return datetime.now(TIMEZONE_ESP)

# Capacidades máximas específicas por zona
ZONE_CAPACITY = {
    "Cardio": 20,
    "Pesas": 20,
    "Piscina": 15,
    "Yoga": 10
}

# Umbral de alerta de ocupación (80%)
OCCUPATION_ALERT_THRESHOLD = 0.8

print(f"[DEBUG] Config: RABBITMQ_HOST={RABBITMQ_HOST}")
print(f"[DEBUG] Config: MONGO_URI={MONGO_URI}")

try:
    print("[DEBUG] Conectando a MongoDB...")
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['gym']
    collection = db['events']
    alerts_collection = db['alerts']  # Colección separada para alertas
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

    # Declarar el exchange
    channel.exchange_declare(exchange='gym_events', exchange_type='direct')

    # Declarar una cola exclusiva para este consumidor
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Vincular la cola al exchange con las claves de enrutamiento que necesites
    routing_keys = ['entrada', 'salida']
    for key in routing_keys:
        channel.queue_bind(exchange='gym_events', queue=queue_name, routing_key=key)
    
    print("[DEBUG] Conexión a RabbitMQ establecida")
except Exception as e:
    print(f"[ERROR] Error conectando a RabbitMQ: {e}")
    raise e

def calculate_zone_occupation():
    """Calcula la ocupación actual de cada zona de forma precisa"""
    # Obtener todos los eventos ordenados por timestamp
    eventos = list(collection.find({
        "evento": {"$in": ["entrada", "salida"]},
    }).sort("timestamp", 1))
    
    # Rastrear usuarios activos por zona
    usuarios_por_zona = {zona: set() for zona in ZONE_CAPACITY.keys()}
    user_current_location = {}  # Diccionario para rastrear ubicación actual de usuarios
    
    # Procesar los eventos cronológicamente
    for evento in eventos:
        usuario_id = evento.get("usuario_id")
        zona = evento.get("zona")
        tipo = evento.get("evento")
        
        if not zona or not usuario_id:
            continue
            
        if tipo == "entrada":
            # Si el usuario ya estaba en otra zona, quitarlo de ahí primero
            if usuario_id in user_current_location:
                zona_anterior = user_current_location[usuario_id]
                if zona_anterior in usuarios_por_zona:
                    usuarios_por_zona[zona_anterior].discard(usuario_id)
            
            # Registrar entrada a la nueva zona
            user_current_location[usuario_id] = zona
            if zona in usuarios_por_zona:
                usuarios_por_zona[zona].add(usuario_id)
        
        elif tipo == "salida":
            # Registrar salida
            if usuario_id in user_current_location:
                zona_salida = user_current_location[usuario_id]
                if zona_salida in usuarios_por_zona:
                    usuarios_por_zona[zona_salida].discard(usuario_id)
                del user_current_location[usuario_id]
    
    # Calcular porcentaje de ocupación por zona
    ocupacion = {}
    for zona, usuarios in usuarios_por_zona.items():
        capacidad = ZONE_CAPACITY.get(zona, 20)
        usuarios_actuales = len(usuarios)
        porcentaje = (usuarios_actuales / capacidad) * 100 if capacidad > 0 else 0
        
        ocupacion[zona] = {
            "usuarios": usuarios_actuales,
            "capacidad": capacidad,
            "porcentaje": round(porcentaje, 1)
        }
    
    return ocupacion

def check_occupation_alerts():
    """Verifica periódicamente la ocupación y genera alertas si es necesario"""
    alerted_zones = set()  # Zonas que ya tienen una alerta activa

    while True:
        try:
            ocupacion = calculate_zone_occupation()
            current_time = get_local_time()
            
            for zona, datos in ocupacion.items():
                # Si la ocupación supera el umbral y no hay alerta activa para esta zona
                if (datos["porcentaje"] >= OCCUPATION_ALERT_THRESHOLD * 100) and (zona not in alerted_zones):
                    print(f"[ALERTA] Alta ocupación en {zona}: {datos['porcentaje']}%")
                    
                    # Crear alerta en MongoDB
                    alerta = {
                        "tipo": "ocupacion",
                        "zona": zona,
                        "porcentaje": datos["porcentaje"],
                        "usuarios": datos["usuarios"],
                        "capacidad": datos["capacidad"],
                        "timestamp": current_time,
                        "mensaje": f"Alta ocupación en zona {zona}: {datos['porcentaje']}%"
                    }
                    alerts_collection.insert_one(alerta)
                    alerted_zones.add(zona)
                
                # Si la ocupación baja del umbral, eliminar de las zonas alertadas
                elif (datos["porcentaje"] < OCCUPATION_ALERT_THRESHOLD * 100) and (zona in alerted_zones):
                    alerted_zones.discard(zona)
            
            time.sleep(5)  # Verificar cada 5 segundos
            
        except Exception as e:
            print(f"[ERROR] Error verificando ocupación: {e}")
            time.sleep(10)

def callback(ch, method, properties, body):
    """Procesa eventos individuales de RabbitMQ"""
    try:
        event = json.loads(body)
        print(f"[DEBUG] Evento recibido: {event.get('evento')} - Usuario: {event.get('usuario_id')} - Zona: {event.get('zona')}")
        
        # No es necesario procesar aquí la ocupación, ya que se hace periódicamente
        # Solo procesar alertas específicas por evento
        
        # Por ejemplo, detectar si un usuario entra a una zona que ya está llena
        if event.get("evento") == "entrada":
            zona = event.get("zona")
            if zona:
                ocupacion = calculate_zone_occupation()
                if zona in ocupacion and ocupacion[zona]["porcentaje"] >= 100:
                    alerta = {
                        "tipo": "zona",
                        "zona": zona,
                        "timestamp": get_local_time(),
                        "mensaje": f"Zona {zona} ha alcanzado su capacidad máxima"
                    }
                    alerts_collection.insert_one(alerta)
    except Exception as e:
        print(f"[ERROR] Error procesando evento: {e}")

# Iniciar thread para verificar ocupación periódicamente
Thread(target=check_occupation_alerts, daemon=True).start()

print("[Alert] Esperando eventos...")
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
channel.start_consuming()