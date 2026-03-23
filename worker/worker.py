import json
import os
import time

import pika
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://video_user:video_pass@db:5432/videos"
)

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@rabbitmq:5672/"
)

print("Worker starting...")
print("DATABASE_URL:", DATABASE_URL)
print("RABBITMQ_URL:", RABBITMQ_URL)

engine = create_engine(DATABASE_URL)


def process_video(video_id: int):
    print(f"Processing video {video_id}...")
    time.sleep(3)

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE videos SET status = 'ready' WHERE id = :id"),
            {"id": video_id},
        )

    print(f"Video {video_id} marked as ready.")


def callback(ch, method, properties, body):
    try:
        payload = json.loads(body)
        video_id = payload["video_id"]

        process_video(video_id)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print("Error processing message:", e)


# 🔁 Retry loop (IMPORTANT FIX)
while True:
    try:
        print("Connecting to RabbitMQ...")

        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.queue_declare(queue="video_jobs", durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue="video_jobs", on_message_callback=callback)

        print("Connected! Listening on video_jobs...")
        channel.start_consuming()

    except Exception as e:
        print("Connection failed:", e)
        print("Retrying in 5 seconds...")
        time.sleep(5)