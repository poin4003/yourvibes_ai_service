import http.server
import socketserver
import json
from utils.config_reader import ConfigReader

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "status": "healthy",
                "message": "Server is running",
                "dependencies": {
                    "rabbitmq": "ok"
                }
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_health_check_server(config_env=None):
    config_reader = ConfigReader(config_env)
    server_config = config_reader.get_server_config()
    PORT = server_config.port 

    print(f"Starting health check server on port {PORT}...")
    try:
        server = socketserver.TCPServer(("0.0.0.0", PORT), HealthCheckHandler)
        return server
    except Exception as e:
        print(f"Failed to start health check server: {e}")
        raise

