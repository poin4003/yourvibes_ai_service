# src/broker/producer.py
from utils.rabbitmq_connection import RabbitMQConnection
import json
import pika

class Producer:
    def __init__(self, config_env=None, queue="input_queue"):
        self.connection = RabbitMQConnection(config_env)
        self.channel = self.connection.get_channel()
        self.queue = queue

        # Khai báo queue để đảm bảo queue tồn tại
        self.channel.queue_declare(queue=self.queue, durable=True)

    def publish(self, message):
        try:
            if self.channel is None or self.channel.is_closed:
                self.channel = self.connection.get_channel()

            # Gửi message dưới dạng JSON
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)  # Persistent
            )
            print(f" [x] Sent message to {self.queue}: {message}")
        except Exception as e:
            print(f"Error publishing message: {e}")
            raise

    def close(self):
        self.connection.close()