import json
from datetime import datetime
import pika
from sqlalchemy import text
from app.settings import settings
from app.db import get_db

def stub_predict(distance_km: float, duration_min: float, avg_hr: float | None) -> float:
    base = 80.0 * distance_km
    if avg_hr is not None:
        base += 0.5 * max(0.0, avg_hr - 100.0)
    base += 0.2 * duration_min
    return float(round(base, 2))

def process_message(ch, method, properties, body: bytes):
    payload = json.loads(body.decode("utf-8"))
    workout_id = payload["workout_id"]
    prediction_id = payload["prediction_id"]

    db = get_db()
    try:
        w = db.execute(
            text("""
                SELECT distance_km, duration_min, avg_hr
                FROM workouts
                WHERE workout_id = :workout_id
            """),
            {"workout_id": workout_id},
        ).mappings().first()

        if w is None:
            db.execute(
                text("""
                    UPDATE predictions
                    SET status='failed', processed_at=:processed_at, model_version=:model_version
                    WHERE prediction_id = :prediction_id
                """),
                {
                    "prediction_id": prediction_id,
                    "processed_at": datetime.utcnow(),
                    "model_version": settings.model_version,
                },
            )
            db.commit()
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        calories = stub_predict(
            distance_km=float(w["distance_km"] or 0.0),
            duration_min=float(w["duration_min"] or 0.0),
            avg_hr=(float(w["avg_hr"]) if w["avg_hr"] is not None else None),
        )

        db.execute(
            text("""
                UPDATE predictions
                SET status='done',
                    calories_pred=:calories_pred,
                    model_version=:model_version,
                    processed_at=:processed_at
                WHERE prediction_id = :prediction_id
            """),
            {
                "prediction_id": prediction_id,
                "calories_pred": calories,
                "model_version": settings.model_version,
                "processed_at": datetime.utcnow(),
            },
        )
        db.commit()
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        db.rollback()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    finally:
        db.close()

def main():
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=settings.queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(queue=settings.queue_name, on_message_callback=process_message)
    print(f"[worker] consuming queue={settings.queue_name}", flush=True)
    channel.start_consuming()

if __name__ == "__main__":
    main()
