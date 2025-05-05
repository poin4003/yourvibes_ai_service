import os
import yaml
import threading

class ConfigReader:
    _instance = None
    _lock = threading.Lock()
    _initialized = threading.Event() 

    def __new__(cls, config_env=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigReader, cls).__new__(cls)
                cls._instance._init(config_env)
                cls._initialized.set()  
        cls._initialized.wait() 
        return cls._instance

    def _init(self, config_env):
        self.config_env = config_env or os.getenv("YOURVIBES_AI_CONFIG_FILE", "dev")
        self.config_path = os.path.join("config", f"{self.config_env}.yaml")
        self.config = self.load_config()

    def load_config(self):
        print(self.config_env)
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise Exception(f"Config file {self.config_path} not found")
        except Exception as e:
            raise Exception(f"Error loading config file {self.config_path}: {str(e)}")

    def get_server_config(self):
        server_config = self.config.get("server", {})
        return Server(server_config)

    def get_rabbitmq_config(self):
        rabbitmq_config = self.config.get("rabbitmq", {})
        return RabbitMQConfig(rabbitmq_config)

    def get_comment_censor_grpc_conn_config(self):
        comment_censor_grpc_conn = self.config.get("comment_censor_grpc_conn", {})
        return CommentCensorGrpcConn(comment_censor_grpc_conn)

class Server:
    def __init__(self, config_dict):
        self.port = config_dict.get("port", 5000)

class RabbitMQConfig:
    def __init__(self, config_dict):
        self.url = config_dict.get("url", "amqp://guest:guest@localhost:5672/")
        self.username = config_dict.get("username", "guest")
        self.password = config_dict.get("password", "guest")
        self.vhost = config_dict.get("vhost", "/")
        self.connection_timeout = config_dict.get("connection_timeout", 10)
        self.max_reconnect_attempts = config_dict.get("max_reconnect_attempts", 5)

class CommentCensorGrpcConn:
    def __init__(self, config_dict):
        self.host = config_dict.get("host", "localhost")
        self.port = config_dict.get("port", 50051)
