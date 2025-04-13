import pika
import time
from utils.config_reader import ConfigReader

class RabbitMQConnection:
    _instance = None  

    def __new__(cls, config_env=None):
        if cls._instance is None:
            cls._instance = super(RabbitMQConnection, cls).__new__(cls)
            config_reader = ConfigReader(config_env)
            rabbitmq_config = config_reader.get_rabbitmq_config()

            cls._instance.host = rabbitmq_config.host
            cls._instance.port = rabbitmq_config.port
            cls._instance.username = rabbitmq_config.username
            cls._instance.password = rabbitmq_config.password
            cls._instance.connection_timeout = rabbitmq_config.connection_timeout
            cls._instance.max_reconnect_attempts = rabbitmq_config.max_reconnect_attempts

            cls._instance.connection = None
            cls._instance.channel = None
            cls._instance.connect()  
        return cls._instance

    def connect(self):
        attempt = 0
        while attempt < self.max_reconnect_attempts:
            try:
                credentials = pika.PlainCredentials(self.username, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials,
                    connection_attempts=self.max_reconnect_attempts,
                    socket_timeout=self.connection_timeout
                )
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                print(f"Connected to RabbitMQ at {self.host}:{self.port}")
                return True
            except Exception as e:
                attempt += 1
                print(f"Connection attempt {attempt}/{self.max_reconnect_attempts} failed: {e}")
                if attempt == self.max_reconnect_attempts:
                    print("Max reconnect attempts reached. Exiting.")
                    return False
                time.sleep(2)

    def get_channel(self):
        if self.channel is None or self.channel.is_closed:
            self.connect()
        return self.channel

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            print("RabbitMQ connection closed")
            RabbitMQConnection._instance = None