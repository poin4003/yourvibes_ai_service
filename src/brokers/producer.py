import json
import pika
from utils.rabbitmq_connection import RabbitMQConnection
from consts.consts import CREATE_POST_EXCHANGE, CREATE_POST_QUEUE
from dtos.dto import PostModerationResponse

class Producer:
    def __init__(self):
        self.connection = RabbitMQConnection()
        self.channel = self.connection.get_channel()
        self.exchange = CREATE_POST_EXCHANGE
        self.queue = CREATE_POST_QUEUE

    def publish(self, message: PostModerationResponse):
        print("send message create post for main server")
        try:
            if self.channel is None or self.channel.is_closed:
                self.channel = self.connection.get_channel()

            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.queue,
                body=json.dumps(message.to_dict()),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            print(f" [x] Sent message to {self.queue} via {self.exchange}: {message.to_dict()}")
        except Exception as e:
            print(f"Error publishing message: {e}")
            raise

    def close(self):
        pass