import threading
import time
from brokers.consumer import Consumer
from api.health_check import run_health_check_server
from api.comment_censor import serve
from utils.rabbitmq_connection import RabbitMQConnection

def start_consumer():
    try:
        consumer = Consumer()
        consumer.start_consuming()
    except Exception as e:
        print(f"Consumer failed: {e}")
        raise 
    finally:
        consumer.close()

def main():
    print("starting...")
    consumer_thread = threading.Thread(target=start_consumer)
    consumer_thread.daemon = True
    consumer_thread.start()

    grpc_thread = threading.Thread(target=serve)
    grpc_thread.daemon = True 
    grpc_thread.start()

    health_check_server = run_health_check_server() 
    health_check_thread = threading.Thread(target=health_check_server.serve_forever)
    health_check_thread.daemon = True
    health_check_thread.start()

    time.sleep(2)

    try:
        while True:
            if not consumer_thread.is_alive():
                print("Consumer thread stopped unexpectedly. Exiting.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Program failed: {e}")
    finally:
        health_check_server.shutdown()
        health_check_server.server_close()
        rabbitmq_conn = RabbitMQConnection()
        rabbitmq_conn.close()

if __name__ == "__main__":
    main()