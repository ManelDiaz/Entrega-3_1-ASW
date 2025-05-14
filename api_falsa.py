from flask import Flask, jsonify, request
import random
import datetime

app = Flask(__name__)
user_status = {}  # Diccionario para almacenar el estado de cada usuario (0: fuera, 1: dentro)

def current_time():
    return datetime.datetime.utcnow().isoformat() + "Z"

def generate_checkin_event():
    zones = ["Cardio", "Pesas", "Piscina", "Yoga"]
    return {
        "event": "checkin",
        "member_id": random.randint(1, 1000),
        "timestamp": current_time(),
        "zone": random.choice(zones)
    }

def generate_checkout_event():
    return {
        "event": "checkout",
        "member_id": random.randint(1, 1000),
        "timestamp": current_time()
    }

def generate_class_event():
    classes = ["Yoga", "Pilates", "Spinning", "CrossFit"]
    instructors = ["Alice", "Bob", "Charlie", "Diana"]
    schedules = ["08:00", "10:00", "14:00", "18:00"]
    return {
        "event": "class",
        "member_id": random.randint(1, 1000),
        "timestamp": current_time(),
        "class_name": random.choice(classes),
        "instructor": random.choice(instructors),
        "schedule": random.choice(schedules)
    }

@app.route('/simulate', methods=['GET'])
def simulate_event():
    # Se elige aleatoriamente uno de los eventos disponibles
    events = [generate_checkin_event, generate_checkout_event, generate_class_event]
    event_func = random.choice(events)
    return jsonify(event_func())

@app.route('/checkin', methods=['GET'])
def checkin():
    return jsonify(generate_checkin_event())

@app.route('/checkout', methods=['GET'])
def checkout():
    return jsonify(generate_checkout_event())

@app.route('/class', methods=['GET'])
def class_event():
    return jsonify(generate_class_event())

@app.route('/update_state', methods=['GET'])
def update_state():
    member_id = request.args.get('member_id')
    accion = request.args.get('accion')
    if member_id is None or accion is None:
        return jsonify({"error": "Faltan parámetros"}), 400
    try:
        member_id = int(member_id)
    except ValueError:
        return jsonify({"error": "member_id debe ser entero"}), 400
    if member_id not in user_status:
        user_status[member_id] = 0  # Valor inicial: fuera
    if accion == "enter":
        if user_status[member_id] == 1:
            return jsonify({"error": "El usuario ya está dentro"}), 400
        user_status[member_id] = 1
        return jsonify({"member_id": member_id, "estado": 1, "message": "Usuario ha entrado"}), 200
    elif accion == "exit":
        if user_status[member_id] == 0:
            return jsonify({"error": "El usuario ya está fuera"}), 400
        user_status[member_id] = 0
        return jsonify({"member_id": member_id, "estado": 0, "message": "Usuario ha salido"}), 200
    else:
        return jsonify({"error": "Acción no válida"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)