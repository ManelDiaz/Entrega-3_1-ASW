import pika, json, time, requests

credentials = pika.PlainCredentials('user', 'bitnami')
parameters = pika.ConnectionParameters('rabbitmq', 5672, '/', credentials)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.queue_declare(queue='gym_events')

while True:
    # Consulta a la API para obtener un evento simulado del gimnasio
    response = requests.get("http://direccion_de_tu_api:5000/simulate")
    if response.status_code == 200:
        event = response.json()
        channel.basic_publish(exchange='', routing_key='gym_events', body=json.dumps(event))
        print(f"[Producer] Evento enviado: {event}")
    else:
        print("[Producer] Error al consultar la API")
    time.sleep(3)
