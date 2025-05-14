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
        USUARIOS_ESTADO[user_id] = False 
    return usuarios

@app.before_first_request
def setup():
    global USUARIOS
    USUARIOS = generar_usuarios(100)

@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    return jsonify(USUARIOS)

def evento_entrada_salida(tipo):
    usuario = random.choice(USUARIOS)
    if tipo == "entrada":
        USUARIOS_ESTADO[usuario["id"]] = True
        zona = random.choice(ZONAS)
    else:
        USUARIOS_ESTADO[usuario["id"]] = False
        zona = None
    return {
        "evento": tipo,
        "usuario_id": usuario["id"],
        "nombre": usuario["nombre"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "zona": zona
    }

@app.route('/evento/entrada', methods=['GET'])
def generar_entrada():
    return jsonify(evento_entrada_salida("entrada"))

@app.route('/evento/salida', methods=['GET'])
def generar_salida():
    return jsonify(evento_entrada_salida("salida"))

@app.route('/evento/random', methods=['GET'])
def generar_evento_random():
    tipo = random.choice(["entrada", "salida"])
    return jsonify(evento_entrada_salida(tipo))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)