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
        USUARIOS_ESTADO[user_id] = False  # Todos fuera al inicio
    return usuarios

@app.before_first_request
def setup():
    global USUARIOS
    USUARIOS = generar_usuarios(100)

@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    return jsonify(USUARIOS)

def evento_entrada():
    fuera = [u for u in USUARIOS if not USUARIOS_ESTADO[u["id"]]]
    if not fuera:
        return None  # No hay nadie fuera
    usuario = random.choice(fuera)
    USUARIOS_ESTADO[usuario["id"]] = True
    zona = random.choice(ZONAS)
    return {
        "evento": "entrada",
        "usuario_id": usuario["id"],
        "nombre": usuario["nombre"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "zona": zona
    }

def evento_salida():
    dentro = [u for u in USUARIOS if USUARIOS_ESTADO[u["id"]]]
    if not dentro:
        return None  # No hay nadie dentro
    usuario = random.choice(dentro)
    USUARIOS_ESTADO[usuario["id"]] = False
    return {
        "evento": "salida",
        "usuario_id": usuario["id"],
        "nombre": usuario["nombre"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "zona": None
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
    posibles = []
    if any(not USUARIOS_ESTADO[u["id"]] for u in USUARIOS):
        posibles.append("entrada")
    if any(USUARIOS_ESTADO[u["id"]] for u in USUARIOS):
        posibles.append("salida")
    if not posibles:
        return jsonify({"error": "No hay eventos posibles"}), 400
    tipo = random.choice(posibles)
    if tipo == "entrada":
        return generar_entrada()
    else:
        return generar_salida()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)