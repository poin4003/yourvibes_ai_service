import threading
import time
from brokers.consumer import Consumer

def start_consumer():
    consumer = Consumer()
    try:
        consumer.start_consuming()
    finally:
        consumer.close()

def main():
    consumer_thread = threading.Thread(target=start_consumer)
    consumer_thread.daemon = True 
    consumer_thread.start()

    time.sleep(2)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    main()