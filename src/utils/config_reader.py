import os
import yaml

class RabbitMQConfig:
    def __init__(self, config_dict):
        self.url = config_dict.get("url", "amqp://guest:guest@localhost:5672/")
        self.username = config_dict.get("username", "guest")
        self.password = config_dict.get("password", "guest")
        self.vhost = config_dict.get("vhost", "/")
        self.connection_timeout = config_dict.get("connection_timeout", 10)
        self.max_reconnect_attempts = config_dict.get("max_reconnect_attempts", 5)

class ConfigReader:
    def __init__(self, config_env=None):
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

    def get_rabbitmq_config(self):
        rabbitmq_config = self.config.get("rabbitmq", {})
        return RabbitMQConfig(rabbitmq_config)