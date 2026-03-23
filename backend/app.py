import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import pika
import redis
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from models import db, Video

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql://video_user:video_pass@localhost:5432/videos"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

db.init_app(app)
with app.app_context():
    db.create_all()


def publish_video_job(video_id: int):
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue="video_jobs", durable=True)
    channel.basic_publish(
        exchange="",
        routing_key="video_jobs",
        body=json.dumps({"video_id": video_id}),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.get("/api/videos")
def list_videos():
    cached = redis_client.get("videos:list")
    if cached:
        return app.response_class(cached, mimetype="application/json")

    videos = Video.query.order_by(Video.created_at.desc()).all()
    data = [video.to_dict() for video in videos]
    payload = json.dumps(data)
    redis_client.setex("videos:list", 60, payload)
    return app.response_class(payload, mimetype="application/json")


@app.get("/api/videos/<int:video_id>")
def get_video(video_id: int):
    cache_key = f"videos:{video_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return app.response_class(cached, mimetype="application/json")

    video = Video.query.get_or_404(video_id)
    payload = json.dumps(video.to_dict())
    redis_client.setex(cache_key, 60, payload)
    return app.response_class(payload, mimetype="application/json")

@app.post("/api/videos/upload")
def upload_video():
    file = request.files.get("video")
    title = request.form.get("title", "Untitled Video")
    description = request.form.get("description", "")

    if not file:
        return jsonify({"error": "No video file uploaded"}), 400

    safe_name = file.filename.replace(" ", "_")
    filepath = UPLOAD_DIR / safe_name
    file.save(filepath)

    video = Video(
        title=title,
        description=description,
        filename=safe_name,
        status="processing",
    )
    db.session.add(video)
    db.session.commit()

    redis_client.delete("videos:list")
    publish_video_job(video.id)

    return jsonify(video.to_dict()), 201

@app.get("/api/videos/<int:video_id>/stream")
def stream_video(video_id: int):
    video = Video.query.get_or_404(video_id)
    filepath = UPLOAD_DIR / video.filename

    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404

    return send_file(filepath, mimetype="video/mp4", conditional=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)