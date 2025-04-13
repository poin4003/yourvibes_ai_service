# src/broker/consumer.py
import json
import pika
import os
from utils.rabbitmq_connection import RabbitMQConnection
from models.text_moderator import TextModerator
from models.image_moderator import ImageModerator
from brokers.producer import Producer
from consts.consts import AI_EXCHANGE, AI_QUEUE, AI_DLX, AI_DLQ
from dtos.dto import PostModerationRequest, PostModerationResponse, ContentResult, MediaResult

class Consumer:
    def __init__(self):
        self.connection = RabbitMQConnection()
        self.channel = self.connection.get_channel()
        self.text_moderator = TextModerator()
        self.image_moderator = ImageModerator()
        self.producer = Producer()

        self.exchange = AI_EXCHANGE
        self.dlx = AI_DLX
        self.queue = AI_QUEUE
        self.dlq = AI_DLQ
        self.max_retries = 3

        self.channel.exchange_declare(exchange=self.exchange, exchange_type="direct")
        self.channel.exchange_declare(exchange=self.dlx, exchange_type="direct")

        self.channel.queue_declare(
            queue=self.queue,
            durable=True,
            arguments={
                "x-message-ttl": 3600000,
                "x-max-length": 10000,
                "x-dead-letter-exchange": self.dlx,
                "x-dead-letter-routing-key": self.dlq,
                "x-overflow": "reject-publish-dlx"
            }
        )

        self.channel.queue_declare(
            queue=self.dlq,
            durable=True,
            arguments={
                "x-message-ttl": 3600000,
                "x-max-length": 10000
            }
        )

        self.channel.queue_bind(
            queue=self.queue,
            exchange=self.exchange,
            routing_key=self.queue
        )

        self.channel.queue_bind(
            queue=self.dlq,
            exchange=self.dlx,
            routing_key=self.dlq
        )

    def callback(self, ch, method, properties, body):
        retries = properties.headers.get("x-retries", 0) if properties.headers else 0

        try:
            message = json.loads(body)
            request = PostModerationRequest(
                post_id=message["post_id"],
                content=message["content"],
                base_url=message["base_url"],
                media=message["media"]
            )

            content_result = self.text_moderator.moderate(request.content)
            content_response = ContentResult(
                label=content_result["label"],
                censored_text=content_result["censored_text"]
            )

            media_label = "normal"
            for media_file in request.media:
                file_path = os.path.join(request.base_url, media_file)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Media file not found: {file_path}")

                media_result = self.image_moderator.moderate(file_path)
                if media_result["label"] in ["nsfw", "violence", "political"]:
                    media_label = media_result["label"]
                    break

            media_response = MediaResult(label=media_label)

            response = PostModerationResponse(
                post_id=request.post_id,
                content=content_response,
                media=media_response
            )
            self.producer.publish(response)

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"Error processing message (attempt {retries + 1}/{self.max_retries}): {e}")

            if retries < self.max_retries:
                headers = properties.headers or {}
                headers["x-retries"] = retries + 1
                ch.basic_publish(
                    exchange=self.exchange,
                    routing_key=self.queue,
                    body=body,
                    properties=pika.BasicProperties(
                        headers=headers,
                        delivery_mode=2
                    )
                )
                print(f"Retrying message: {body}")
            else:
                ch.basic_publish(
                    exchange=self.dlx,
                    routing_key=self.dlq,
                    body=body,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                print(f"Message moved to DLQ after {self.max_retries} retries: {body}")

            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        try:
            print(f" [*] Waiting for messages in {self.queue}. To exit press CTRL+C")
            self.channel.basic_consume(
                queue=self.queue,
                on_message_callback=self.callback,
                auto_ack=False
            )
            self.channel.start_consuming()
        except Exception as e:
            print(f"Error starting consumer: {e}")
            raise

    def close(self):
        self.producer.close()
        self.connection.close()