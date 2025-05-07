import json, time, random
from flask import Flask, jsonify

nombres = ["Juan", "Ana", "Carlos", "María", "Pablo", "Elena", "Miguel", "Sofía", "David", "Laura"]
apellidos = ["García", "Martínez", "López", "Rodríguez", "Sánchez", "Fernández", "González", "Pérez", "Díaz", "Torres"]

generated_users = []

def generate_unique_name():
    """Generate a unique combination of name and surname"""
    
    if len(used_combinations) >= len(nombres) * len(apellidos):
        used_combinations.clear()
    
    while True:
        nombre = random.choice(nombres)
        apellido = random.choice(apellidos)
        full_name = f"{nombre} {apellido}"
        
        if full_name not in used_combinations:
            used_combinations.add(full_name)
            return full_name

app = Flask(__name__)

@app.route('/api/members/batch/<int:count>', methods=['GET'])
def get_multiple_members(count):
    
    if count > 100:  # Limit batch size
        count = 100
        
    members = []
    for _ in range(count):
        gym_member = {
            "id": random.randint(1000, 9999),
            "nombre": generate_unique_name(),
            "estado": random.choice([True, False]),
            "membresía": random.choice(["básica", "estándar", "premium", "vip"]),
        }
        members.append(gym_member)
        
    return jsonify(members)

@app.route('/api/members/entradas_salidas', methods=['GET'])
def generate_entradas_salidas():

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)