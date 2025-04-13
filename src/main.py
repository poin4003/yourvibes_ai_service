# src/main.py
import threading
import time
from brokers.consumer import Consumer
from brokers.producer import Producer

def start_consumer():
    consumer = Consumer()
    try:
        consumer.start_consuming()
    finally:
        consumer.close()

def main():
    # Khởi động consumer trong một thread riêng
    consumer_thread = threading.Thread(target=start_consumer)
    consumer_thread.daemon = True  # Thread sẽ dừng khi main dừng
    consumer_thread.start()

    # Đợi một chút để consumer khởi động
    time.sleep(2)

    # Khởi tạo Producer và gửi message thử nghiệm
    producer = Producer()
    message = {"type": "text", "content": "fuck off"}  # Message thử nghiệm
    try:
        producer.publish(message)
    finally:
        producer.close()

    # Giữ main thread chạy để consumer tiếp tục lắng nghe
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    main()