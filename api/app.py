from flask import Flask, jsonify, request
import random
from datetime import datetime
from faker import Faker

app = Flask(__name__)
fake = Faker('es_ES')

MEMBRESIAS = ["básica", "estándar", "premium", "vip"]
ZONAS = ["Cardio", "Pesas", "Piscina", "Yoga"]

USUARIOS = []
USUARIOS_ESTADO = {}

def generar_usuarios(cantidad):
    usados = set()
    usuarios = []
    while len(usuarios) < cantidad:
        nombre = fake.first_name()
        apellido = fake.last_name()
        full_name = f"{nombre} {apellido}"
        if full_name in usados:
            continue
        usados.add(full_name)
        user_id = len(usuarios) + 1
        usuario = {
            "id": user_id,
            "nombre": full_name,
            "membresia": random.choice(MEMBRESIAS)
        }
        usuarios.append(usuario)
        USUARIOS_ESTADO[user_id] = None  # Todos fuera al inicio
    print(f"[DEBUG] Usuarios generados: {usuarios}")
    print(f"[DEBUG] Estado inicial de usuarios: {USUARIOS_ESTADO}")
    return usuarios

@app.route('/inicializar', methods=['POST'])
def inicializar():
    global USUARIOS
    cantidad = request.json.get('cantidad', 100)
    USUARIOS = generar_usuarios(cantidad)
    print(f"[DEBUG] Usuarios inicializados: {USUARIOS}")
    print(f"[DEBUG] Estado inicial de usuarios: {USUARIOS_ESTADO}")
    return jsonify({"mensaje": f"Se han generado {len(USUARIOS)} usuarios"})


@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    return jsonify(USUARIOS)

def evento_entrada():
    fuera = [u for u in USUARIOS if USUARIOS_ESTADO[u["id"]] is None]
    print(f"[DEBUG] Usuarios fuera: {fuera}")
    if not fuera:
        return None  # No hay nadie fuera
    usuario = random.choice(fuera)
    zona = random.choice(ZONAS)
    USUARIOS_ESTADO[usuario["id"]] = zona  # Registrar la zona del usuario
    print(f"[DEBUG] Usuario {usuario['id']} entró a la zona {zona}")
    return {
        "evento": "entrada",
        "usuario_id": usuario["id"],
        "nombre": usuario["nombre"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "zona": zona
    }

def evento_salida():
    dentro = [u for u in USUARIOS if USUARIOS_ESTADO[u["id"]] is not None]
    print(f"[DEBUG] Usuarios dentro: {dentro}")
    if not dentro:
        return None  # No hay nadie dentro
    usuario = random.choice(dentro)
    zona_actual = USUARIOS_ESTADO[usuario["id"]]  # Obtener la zona actual
    USUARIOS_ESTADO[usuario["id"]] = None  # Marcar al usuario como fuera
    print(f"[DEBUG] Usuario {usuario['id']} salió de la zona {zona_actual}")
    return {
        "evento": "salida",
        "usuario_id": usuario["id"],
        "nombre": usuario["nombre"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "zona": zona_actual
    }

@app.route('/evento/entrada', methods=['GET'])
def generar_entrada():
    evento = evento_entrada()
    if evento:
        return jsonify(evento)
    return jsonify({"error": "No hay usuarios fuera"}), 400

@app.route('/evento/salida', methods=['GET'])
def generar_salida():
    evento = evento_salida()
    if evento:
        return jsonify(evento)
    return jsonify({"error": "No hay usuarios dentro"}), 400

@app.route('/evento/random', methods=['GET'])
def generar_evento_random():
    print(f"[DEBUG] Estado actual de usuarios: {USUARIOS_ESTADO}")
    try:
        if any(USUARIOS_ESTADO[u["id"]] is not None for u in USUARIOS):
            # Generar un evento de salida
            evento = evento_salida()
        else:
            # Generar un evento de entrada
            evento = evento_entrada()

        if evento:
            print(f"[DEBUG] Evento generado: {evento}")
            return jsonify(evento)
        print("[DEBUG] No se pudo generar un evento")
        return jsonify({"error": "No se pudo generar un evento"}), 400
    except KeyError as e:
        print(f"[ERROR] KeyError: {e}")
        return jsonify({"error": f"Usuario no encontrado: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)