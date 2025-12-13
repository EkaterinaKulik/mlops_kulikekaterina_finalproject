import json
import pika
from .settings import settings

def publish_message(payload: dict) -> None:
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.queue_declare(queue=settings.queue_name, durable=True)
        body = json.dumps(payload).encode("utf-8")
        channel.basic_publish(
            exchange="",
            routing_key=settings.queue_name,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        connection.close()
