import pika
import json
import os
import time
from collections import Counter
from threading import Thread
from pymongo import MongoClient
import datetime

# Configuración de RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq-service")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "bitnami")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")

print("[DEBUG] Iniciando consumer de estadísticas...")

# Conexión a MongoDB
try:
    print("[DEBUG] Conectando a MongoDB...")
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['gym']
    stats_collection = db['stats']
    events_collection = db['events']
    print("[DEBUG] Conexión a MongoDB establecida")
except Exception as e:
    print(f"[ERROR] Error conectando a MongoDB: {e}")
    raise e

# Conexión a RabbitMQ
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

# Contadores globales
event_counter = Counter()
zone_counter = Counter()
active_users = set()
user_locations = {}  # Nuevo diccionario para rastrear la ubicación de cada usuario
zone_capacity = {
    "Cardio": 20,
    "Pesas": 20,
    "Piscina": 15,
    "Yoga": 10
}

def calculate_zone_stats():
    """Calcula estadísticas detalladas por zona"""
    stats = {}
    
    # Obtener el inicio del día actual en UTC
    today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Obtener todos los eventos ordenados por timestamp
    eventos = list(events_collection.find({
        "evento": {"$in": ["entrada", "salida"]},
        "timestamp": {"$gte": today.isoformat() + "Z"}
    }).sort("timestamp", 1))
    
    # Rastrear usuarios activos por zona
    usuarios_por_zona = {}
    usuarios_activos = set()
    user_current_location = {}  # Diccionario para rastrear la ubicación actual de cada usuario
    
    # Procesar todos los eventos cronológicamente para determinar la ubicación actual
    for evento in eventos:
        usuario_id = evento.get("usuario_id")
        zona = evento.get("zona")
        tipo = evento.get("evento")
        
        if not zona or not usuario_id:
            continue
            
        if tipo == "entrada":
            # Registrar entrada: el usuario ahora está en esta zona
            user_current_location[usuario_id] = zona
            usuarios_activos.add(usuario_id)
        elif tipo == "salida":
            # Registrar salida: el usuario ya no está en ninguna zona
            if usuario_id in user_current_location:
                del user_current_location[usuario_id]
            usuarios_activos.discard(usuario_id)
    
    # Ahora contamos usuarios por zona basado en su ubicación actual
    for usuario_id, zona in user_current_location.items():
        if zona not in usuarios_por_zona:
            usuarios_por_zona[zona] = set()
        usuarios_por_zona[zona].add(usuario_id)
    
    # Calcular estadísticas por zona
    for zona in ["Cardio", "Pesas", "Piscina", "Yoga"]:
        ocupacion_actual = len(usuarios_por_zona.get(zona, set()))
        capacidad = zone_capacity.get(zona, 20)
        porcentaje = (ocupacion_actual / capacidad) * 100 if capacidad > 0 else 0
        
        # Contar entradas y salidas totales por zona
        entradas = events_collection.count_documents({
            "evento": "entrada",
            "zona": zona,
            "timestamp": {"$gte": today.isoformat() + "Z"}
        })
        salidas = events_collection.count_documents({
            "evento": "salida",
            "zona": zona,
            "timestamp": {"$gte": today.isoformat() + "Z"}
        })
        
        stats[zona] = {
            "ocupacion_actual": ocupacion_actual,
            "capacidad": capacidad,
            "porcentaje": round(min(porcentaje, 100), 1),
            "total_entradas": entradas,
            "total_salidas": salidas
        }
        
        print(f"[DEBUG] Stats para {zona}: Ocupación={ocupacion_actual}, Entradas={entradas}, Salidas={salidas}")
    
    # Verificación de consistencia
    total_por_zonas = sum(len(usuarios_por_zona.get(zona, set())) for zona in ["Cardio", "Pesas", "Piscina", "Yoga"])
    total_usuarios_activos = len(usuarios_activos)
    
    # Si hay discrepancia, usar el conteo por zonas como la fuente de verdad
    if total_por_zonas != total_usuarios_activos:
        print(f"[WARNING] Discrepancia en conteo: total={total_usuarios_activos}, suma_zonas={total_por_zonas}")
        # Usar el conteo por zonas como valor correcto
        total_usuarios_activos = total_por_zonas
    
    print(f"[DEBUG] Total usuarios activos: {total_usuarios_activos}, suma por zonas: {total_por_zonas}")
    
    return stats, total_usuarios_activos

def save_stats():
    """Guarda las estadísticas en MongoDB"""
    while True:
        try:
            current_time = datetime.datetime.utcnow()
            zone_stats, total_activos = calculate_zone_stats()
            
            stats = {
                "timestamp": current_time,
                "eventos_tipo": dict(event_counter),
                "ocupacion_zonas": zone_stats,
                "usuarios_activos": total_activos  # Ahora usamos el total calculado de la misma manera que las zonas
            }
            
            stats_collection.insert_one(stats)
            print(f"[DEBUG] Estadísticas guardadas: usuarios_activos={total_activos}, zonas={zone_stats}")
            
            time.sleep(60)  # Actualizar cada minuto
            
        except Exception as e:
            print(f"[ERROR] Error guardando estadísticas: {e}")
            time.sleep(10)
            
            
def callback(ch, method, properties, body):
    try:
        print("[DEBUG] Evento recibido")
        event = json.loads(body)
        tipo = event.get("evento", "otro")
        usuario_id = event.get("usuario_id")
        zona = event.get("zona", "desconocida")
        event_counter[tipo] += 1

        if tipo == "entrada":
            # Registrar la entrada del usuario en la zona
            zone_counter[zona] += 1
            active_users.add(usuario_id)
            user_locations[usuario_id] = zona  # Asociar al usuario con la zona
            print(f"[DEBUG] Usuario {usuario_id} entró a la zona {zona}")

        elif tipo == "salida":
            # Registrar la salida del usuario
            if usuario_id in user_locations:
                zona_anterior = user_locations.pop(usuario_id)  # Obtener y eliminar la zona del usuario
                zone_counter[zona_anterior] -= 1  # Restar la salida de la zona correspondiente
                print(f"[DEBUG] Usuario {usuario_id} salió de la zona {zona_anterior}")
            else:
                print(f"[WARNING] Usuario {usuario_id} no estaba registrado en ninguna zona")
            active_users.discard(usuario_id)

        # Insertar el evento en MongoDB
        events_collection.insert_one(event)
        print(f"[DEBUG] Evento insertado en MongoDB: {event}")

        print(f"[DEBUG] Evento procesado: {event}")
    except Exception as e:
        print(f"[ERROR] Error procesando evento: {e}")

# Iniciar thread para guardar estadísticas
Thread(target=save_stats, daemon=True).start()

print("[Stats] Esperando eventos...")
channel.basic_consume(queue='gym_events', on_message_callback=callback, auto_ack=True)
channel.start_consuming()