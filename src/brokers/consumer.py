import json
import pika
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

    def process_message(self, body, properties):
        print("receive message from main server")
        try:
            # Parse message
            message = json.loads(body)
            print(f"Received message: {message}")

            content = message.get("content", None)  
            media = message.get("media", [])  
            base_url = message.get("base_url", "")  

            request = PostModerationRequest(
                post_id=message["post_id"],
                content=content,
                base_url=base_url,
                media=media
            )

            if content and content.strip():
                content_result = self.text_moderator.moderate(request.content)
                content_response = ContentResult(
                    label=content_result["label"],
                    censored_text=content_result["censored_text"]
                )
            else:
                content_response = ContentResult(
                    label="normal",
                    censored_text=""
                )

            media_label = "normal"
            if media: 
                for media_file in media:
                    media_result = self.image_moderator.moderate(request.base_url, media_file)
                    if media_result["label"] == "error":
                        media_label = "error"
                        break
                    elif media_result["label"] in ["nsfw", "violence", "political", "abuse"]:
                        media_label = media_result["label"]
                        break
                    else:
                        media_label = "normal"

            media_response = MediaResult(label=media_label)

            response = PostModerationResponse(
                post_id=request.post_id,
                content=content_response,
                media=media_response
            )

            print("send message create post for main server")
            self.producer.publish(response)
            return True

        except Exception as e:
            print(f"Error processing message: {e}")
            return False

    def callback(self, ch, method, properties, body):
        success = self.process_message(body, properties)
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def dlq_callback(self, ch, method, properties, body):
        count = 0
        if properties.headers and "x-death" in properties.headers:
            for death in properties.headers["x-death"]:
                if death.get("queue") == self.queue and "count" in death:
                    count = death["count"]
                    break

        print(f"Processing DLQ message (retry count: {count})")

        if count < self.max_retries:
            success = self.process_message(body, properties)
            if success:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                ch.basic_publish(
                    exchange=self.exchange,
                    routing_key=self.queue,
                    body=body,
                    properties=pika.BasicProperties(
                        headers=properties.headers,
                        delivery_mode=2
                    )
                )
                print(f"Republishing message to {self.queue}: {body}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            print(f"Max retries ({self.max_retries}) reached, discarding message: {body}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_consuming(self):
        try:
            print(f" [*] Waiting for messages in {self.queue}. To exit press CTRL+C")
            self.channel.basic_consume(
                queue=self.queue,
                on_message_callback=self.callback,
                auto_ack=False
            )
            self.channel.basic_consume(
                queue=self.dlq,
                on_message_callback=self.dlq_callback,
                auto_ack=False
            )
            self.channel.start_consuming()
        except Exception as e:
            print(f"Error starting consumer: {e}")
            raise

    def close(self):
        self.producer.close()
        self.connection.close()