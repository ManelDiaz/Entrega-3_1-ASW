from flask import Flask, render_template
from pymongo import MongoClient
import os

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['gym']
collection = db['events']

def get_stats():
    total_eventos = collection.count_documents({})
    eventos_tipo = collection.aggregate([
        {"$group": {"_id": "$evento", "count": {"$sum": 1}}}
    ])
    eventos_tipo = {e["_id"]: e["count"] for e in eventos_tipo}
    usuarios_activos = len(set(
        e["usuario_id"] for e in collection.find({"evento": "entrada"})
    )) - len(set(
        e["usuario_id"] for e in collection.find({"evento": "salida"})
    ))
    return total_eventos, eventos_tipo, max(usuarios_activos, 0)

def get_alertas():
    # Ejemplo: alertas por entradas en zona Cardio
    alertas = list(collection.find({"evento": "entrada", "zona": "Cardio"}).sort("timestamp", -1).limit(10))
    return alertas

@app.route("/")
def index():
    total_eventos, eventos_tipo, usuarios_activos = get_stats()
    alertas = get_alertas()
    return render_template(
        "index.html",
        total_eventos=total_eventos,
        eventos_tipo=eventos_tipo,
        usuarios_activos=usuarios_activos,
        alertas=alertas
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)