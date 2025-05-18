from flask import Flask, render_template
from pymongo import MongoClient
import os
import datetime
from datetime import timezone, timedelta


app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['gym']
collection = db['events']
stats_collection = db['stats']
alerts_collection = db['alerts']

TIMEZONE_OFFSET = 2
TIMEZONE_ESP = timezone(timedelta(hours=TIMEZONE_OFFSET))

def get_local_time():
    """Devuelve la hora actual en la zona horaria española"""
    return datetime.datetime.now(TIMEZONE_ESP)


# Capacidades máximas por zona (igual que en consumer_estadisticas.py)
ZONE_CAPACITY = {
    "Cardio": 20,
    "Pesas": 20,
    "Piscina": 15,
    "Yoga": 10
}

def calculate_stats_realtime():
    """Calcula estadísticas en tiempo real con total consistencia"""
    start_time = get_local_time()
    print(f"[DEBUG] Iniciando cálculo en tiempo real: {start_time}")
    
    total_eventos = collection.count_documents({})
    
    # Obtener eventos por tipo
    eventos_tipo_cursor = collection.aggregate([
        {"$group": {"_id": "$evento", "count": {"$sum": 1}}}
    ])
    eventos_tipo = {e["_id"]: e["count"] for e in eventos_tipo_cursor}
    
    today = get_local_time().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Obtener todos los eventos de entrada/salida para determinar el estado actual
    eventos = list(collection.find({
        "evento": {"$in": ["entrada", "salida"]},
    }).sort("timestamp", 1))
    
    # Estructuras para seguimiento preciso
    user_current_location = {}  # Ubicación actual de cada usuario (última zona donde entró)
    usuarios_por_zona = {zona: set() for zona in ZONE_CAPACITY.keys()}  # Sets de usuarios por zona
    
    # Rastrear todos los eventos cronológicamente para determinar la ubicación actual de cada usuario
    for evento in eventos:
        usuario_id = evento.get("usuario_id")
        zona = evento.get("zona")
        tipo = evento.get("evento")
        
        if not zona or not usuario_id:
            continue
        
        if tipo == "entrada":
            # Si el usuario ya estaba en otra zona sin registro de salida, corregir
            if usuario_id in user_current_location:
                zona_anterior = user_current_location[usuario_id]
                if zona_anterior in usuarios_por_zona and usuario_id in usuarios_por_zona[zona_anterior]:
                    usuarios_por_zona[zona_anterior].remove(usuario_id)
                    print(f"[DEBUG] Corregido: Usuario {usuario_id} cambió de zona {zona_anterior} a {zona}")
            
            # Registrar entrada en la nueva zona
            user_current_location[usuario_id] = zona
            if zona in usuarios_por_zona:
                usuarios_por_zona[zona].add(usuario_id)
                
        elif tipo == "salida":
            # Registrar salida (eliminar de la zona y de usuarios activos)
            if usuario_id in user_current_location:
                zona_salida = user_current_location[usuario_id]
                if zona_salida in usuarios_por_zona and usuario_id in usuarios_por_zona[zona_salida]:
                    usuarios_por_zona[zona_salida].remove(usuario_id)
                del user_current_location[usuario_id]
    
    # Calcular estadísticas por zona basadas en los sets mantenidos
    stats_zonas = {}
    for zona in ZONE_CAPACITY.keys():
        ocupacion_actual = len(usuarios_por_zona[zona])
        capacidad = ZONE_CAPACITY.get(zona)
        porcentaje = (ocupacion_actual / capacidad) * 100 if capacidad > 0 else 0
        
        # Eventos del día por zona
        entradas = collection.count_documents({
            "evento": "entrada",
            "zona": zona,
            "timestamp": {"$gte": today.isoformat() + "Z"}
        })
        salidas = collection.count_documents({
            "evento": "salida",
            "zona": zona,
            "timestamp": {"$gte": today.isoformat() + "Z"}
        })
        
        stats_zonas[zona] = {
            "ocupacion_actual": ocupacion_actual,
            "capacidad": capacidad,
            "porcentaje": round(min(porcentaje, 100), 1),
            "total_entradas": entradas,
            "total_salidas": salidas
        }
    
    # El total de usuarios es exactamente la suma de usuarios por zona
    total_usuarios_activos = sum(len(usuarios) for usuarios in usuarios_por_zona.values())
    
    # Verificación para debugging
    print(f"[DEBUG] Usuarios por zona: {', '.join([f'{zona}:{len(usuarios)}' for zona, usuarios in usuarios_por_zona.items()])}")
    print(f"[DEBUG] Total usuarios activos: {total_usuarios_activos}")
    print(f"[DEBUG] Cálculo completado en {(get_local_time() - start_time).total_seconds()}s")
    
    return total_eventos, eventos_tipo, total_usuarios_activos, stats_zonas

# Reemplazar los métodos existentes con el cálculo en tiempo real
def get_stats():
    total_eventos, eventos_tipo, usuarios_activos, _ = calculate_stats_realtime()
    return total_eventos, eventos_tipo, usuarios_activos

def get_movimientos():
    movimientos = list(collection.find(
        {"evento": {"$in": ["entrada", "salida"]}}
    ).sort("timestamp", -1).limit(50))
    return movimientos

def get_alertas():
    # Buscar alertas en la nueva colección específica de alertas
    alertas = list(alerts_collection.find().sort("timestamp", -1).limit(10))
    
    # Formatear mensajes de alerta
    for alerta in alertas:
        if alerta.get("tipo") == "ocupacion":
            alerta["mensaje"] = f"Alta ocupación en zona {alerta.get('zona')}: {alerta.get('porcentaje')}%"
        elif alerta.get("tipo") == "equipo":
            alerta["mensaje"] = f"Equipo {alerta.get('id_equipo')} necesita mantenimiento en zona {alerta.get('zona')}"
        elif alerta.get("tipo") == "clase":
            alerta["mensaje"] = f"Clase {alerta.get('nombre')} comenzará en 10 minutos en {alerta.get('sala')}"
        elif alerta.get("tipo") == "usuario":
            alerta["mensaje"] = f"Usuario {alerta.get('id_usuario')} lleva más de 2 horas en {alerta.get('zona')}"
        elif alerta.get("tipo") == "zona":
            alerta["mensaje"] = f"Zona {alerta.get('zona')} ha alcanzado su capacidad máxima"
    
    return alertas

def get_estadisticas_zonas():
    _, _, _, stats_zonas = calculate_stats_realtime()
    return stats_zonas

@app.route("/")
def index():
    # Calcular todas las estadísticas de una sola vez para total consistencia
    total_eventos, eventos_tipo, usuarios_activos, estadisticas_zonas = calculate_stats_realtime()
    alertas = get_alertas()
    movimientos = get_movimientos()
    
    timestamp = get_local_time().strftime("%d/%m/%Y %H:%M:%S")
    print(f"[INFO] Datos actualizados: {timestamp}, usuarios={usuarios_activos}, zonas={sum(stats['ocupacion_actual'] for stats in estadisticas_zonas.values())}")
    
    return render_template(
        "index.html",
        total_eventos=total_eventos,
        eventos_tipo=eventos_tipo,
        usuarios_activos=usuarios_activos,
        alertas=alertas,
        movimientos=movimientos,
        estadisticas_zonas=estadisticas_zonas,
        timestamp=timestamp
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)