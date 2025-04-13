import json
from utils.rabbitmq_connection import RabbitMQConnection
from models.text_moderator import TextModerator

class Consumer:
    def __init__(self, config_env=None, queue="input_queue"):
        self.connection = RabbitMQConnection(config_env)
        self.channel = self.connection.get_channel()
        self.queue = queue
        self.text_moderator = TextModerator()

        self.channel.queue_declare(queue=self.queue, durable=True)

    def callback(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            content_type = message.get("type")
            content = message.get("content")

            if content_type != "text":
                print(f"Skipping non-text message: {message}")
                return

            result = self.text_moderator.moderate(content)
            print(f"Processed text: {content}")
            print(f"Result: {result}")

        except Exception as e:
            print(f"Error processing message: {e}")

    def start_consuming(self):
        try:
            print(f" [*] Waiting for messages in {self.queue}. To exit press CTRL+C")
            self.channel.basic_consume(
                queue=self.queue,
                on_message_callback=self.callback,
                auto_ack=True
            )
            self.channel.start_consuming()
        except Exception as e:
            print(f"Error starting consumer: {e}")
            raise

    def close(self):
        self.connection.close()