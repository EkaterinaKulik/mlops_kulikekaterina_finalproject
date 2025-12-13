import json
from datetime import datetime

import pika
import pandas as pd
from sqlalchemy import text

from app.settings import settings
from app.db import get_db
from app.model_loader import load_model_and_features

MODEL, FEATURE_COLS, CAT_COLS, MODEL_VERSION_FROM_FILE = load_model_and_features("/app/models")


def _normalize_gender(value: str) -> str:
    # Normalize to "Male"/"Female" like in training
    v = (value or "").strip().title()
    if v in {"M", "Man", "Male"}:
        return "Male"
    if v in {"F", "Woman", "Female"}:
        return "Female"
    return v  # fallback


def _safe_float(x, default: float = 0.0) -> float:
    if x is None:
        return default
    try:
        return float(x)
    except Exception:
        return default


def process_message(ch, method, properties, body: bytes):
    payload = json.loads(body.decode("utf-8"))
    workout_id = payload["workout_id"]
    prediction_id = payload["prediction_id"]

    db = get_db()
    try:
        # Join workouts + users to get full feature set (must match training)
        w = db.execute(
            text(
                """
                SELECT
                    w.duration_min,
                    w.speed_kmh,
                    w.distance_km,
                    w.avg_hr,
                    u.sex,
                    u.age,
                    u.height_cm,
                    u.weight_kg
                FROM workouts w
                JOIN users u ON u.user_id = w.user_id
                WHERE w.workout_id = :workout_id
                """
            ),
            {"workout_id": workout_id},
        ).mappings().first()

        if w is None:
            model_version = MODEL_VERSION_FROM_FILE or settings.model_version
            db.execute(
                text(
                    """
                    UPDATE predictions
                    SET status='failed',
                        processed_at=:processed_at,
                        model_version=:model_version
                    WHERE prediction_id = :prediction_id
                    """
                ),
                {
                    "prediction_id": prediction_id,
                    "processed_at": datetime.utcnow(),
                    "model_version": model_version,
                },
            )
            db.commit()
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Build a single-row feature dict EXACTLY as in Kaggle dataset columns
        row_features = {
            "Gender": _normalize_gender(str(w["sex"])),
            "Age": _safe_float(w["age"]),
            "Height(cm)": _safe_float(w["height_cm"]),
            "Weight(kg)": _safe_float(w["weight_kg"]),
            "Running Time(min)": _safe_float(w["duration_min"]),
            "Running Speed(km/h)": _safe_float(w["speed_kmh"]),
            "Distance(km)": _safe_float(w["distance_km"]),
            "Average Heart Rate": _safe_float(w["avg_hr"]),
        }

        # Respect the exact feature order from features.json
        X = pd.DataFrame([[row_features[c] for c in FEATURE_COLS]], columns=FEATURE_COLS)

        pred = MODEL.predict(X)
        calories = float(pred[0]) if hasattr(pred, "__len__") else float(pred)

        model_version = MODEL_VERSION_FROM_FILE or settings.model_version

        db.execute(
            text(
                """
                UPDATE predictions
                SET status='done',
                    calories_pred=:calories_pred,
                    model_version=:model_version,
                    processed_at=:processed_at
                WHERE prediction_id = :prediction_id
                """
            ),
            {
                "prediction_id": prediction_id,
                "calories_pred": calories,
                "model_version": model_version,
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
