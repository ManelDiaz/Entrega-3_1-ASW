import pika, json

def callback(ch, method, properties, body):
    event = json.loads(body)
    alert = None
    if event.get("event") == "checkin" and event.get("zone") == "Cardio":
        alert = f"Alerta: Zona Cardio congestionada para member {event.get('member_id')}"
    elif event.get("event") == "class" and event.get("schedule") == "18:00":
        alert = f"Alerta: Clase a las 18:00 concurrida para member {event.get('member_id')}"
    if alert:
        print(f"[Alert Consumer] {alert}")
    else:
        print(f"[Alert Consumer] Evento sin alerta: {event}")

credentials = pika.PlainCredentials('user', 'bitnami')
parameters = pika.ConnectionParameters('rabbitmq', 5672, '/', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.queue_declare(queue='gym_events')
channel.basic_consume(queue='gym_events', on_message_callback=callback, auto_ack=True)
print("[Alert Consumer] Esperando eventos...")
channel.start_consuming()
