import pika, json

def callback(ch, method, properties, body):
    event = json.loads(body)
    print(f"[Log Consumer] Registrando evento: {event}")
    # ...aquí podrías agregar código para guardar el log en un archivo...

credentials = pika.PlainCredentials('user', 'bitnami')
parameters = pika.ConnectionParameters('rabbitmq', 5672, '/', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.queue_declare(queue='gym_events')
channel.basic_consume(queue='gym_events', on_message_callback=callback, auto_ack=True)
print("[Log Consumer] Esperando eventos...")
channel.start_consuming()
