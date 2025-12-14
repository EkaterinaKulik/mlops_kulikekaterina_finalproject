import uuid
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import WorkoutIn, WorkoutCreated, PredictionOut
from .queue import publish_message

from typing import Optional

app = FastAPI(title="FitBurn Rewards API", version="0.1.0")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}


@app.post("/workouts", response_model=WorkoutCreated)
def create_workout(payload: WorkoutIn, db: Session = Depends(get_db)):
    workout_id = uuid.uuid4()
    prediction_id = uuid.uuid4()

    # Upsert user profile (needed for ML features)
    db.execute(
        text(
            """
            INSERT INTO users(user_id, age, sex, height_cm, weight_kg)
            VALUES (:user_id, :age, :sex, :height_cm, :weight_kg)
            ON CONFLICT (user_id) DO UPDATE SET
                age = EXCLUDED.age,
                sex = EXCLUDED.sex,
                height_cm = EXCLUDED.height_cm,
                weight_kg = EXCLUDED.weight_kg
            """
        ),
        {
            "user_id": payload.user_id,
            "age": payload.age,
            "sex": payload.gender,
            "height_cm": payload.height_cm,
            "weight_kg": payload.weight_kg,
        },
    )

    db.execute(
        text(
            """
            INSERT INTO workouts(workout_id, user_id, ts, duration_min, distance_km, avg_hr, speed_kmh)
            VALUES (:workout_id, :user_id, :ts, :duration_min, :distance_km, :avg_hr, :speed_kmh)
            """
        ),
        {
            "workout_id": str(workout_id),
            "user_id": payload.user_id,
            "ts": payload.ts,
            "duration_min": payload.duration_min,
            "distance_km": payload.distance_km,
            "avg_hr": payload.avg_hr,
            "speed_kmh": payload.speed_kmh,
        },
    )

    db.execute(
        text(
            """
            INSERT INTO predictions(prediction_id, workout_id, status)
            VALUES (:prediction_id, :workout_id, 'pending')
            """
        ),
        {"prediction_id": str(prediction_id), "workout_id": str(workout_id)},
    )

    db.commit()

    publish_message({"workout_id": str(workout_id), "prediction_id": str(prediction_id)})

    return {"workout_id": workout_id, "prediction_id": prediction_id, "status": "pending"}


@app.get("/predictions/{workout_id}", response_model=PredictionOut)
def get_prediction(workout_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            """
            SELECT p.workout_id, p.status, p.calories_pred, p.model_version, p.created_at, p.processed_at
            FROM predictions p
            WHERE p.workout_id = :workout_id
            ORDER BY p.created_at DESC
            LIMIT 1
            """
        ),
        {"workout_id": str(workout_id)},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="prediction not found")

    return {
        "workout_id": uuid.UUID(str(row["workout_id"])),
        "status": row["status"],
        "calories_pred": row["calories_pred"],
        "model_version": row["model_version"],
        "created_at": row["created_at"],
        "processed_at": row["processed_at"],
    }

@app.get("/workouts/recent")
def recent_workouts(
    limit: int = 50,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 500))

    sql = """
        SELECT
            w.workout_id,
            w.user_id,
            w.ts,
            w.duration_min,
            w.distance_km,
            w.avg_hr,
            w.speed_kmh,
            u.sex as gender,
            u.age,
            u.height_cm,
            u.weight_kg,
            p.status,
            p.calories_pred,
            p.model_version,
            p.created_at as pred_created_at,
            p.processed_at as pred_processed_at
        FROM workouts w
        JOIN users u ON u.user_id = w.user_id
        LEFT JOIN LATERAL (
            SELECT *
            FROM predictions p2
            WHERE p2.workout_id = w.workout_id
            ORDER BY p2.created_at DESC
            LIMIT 1
        ) p ON true
    """

    params = {}
    if user_id:
        sql += " WHERE w.user_id = :user_id"
        params["user_id"] = user_id

    sql += " ORDER BY w.ts DESC LIMIT :limit"
    params["limit"] = limit

    rows = db.execute(text(sql), params).mappings().all()
    return {"items": [dict(r) for r in rows]}


@app.get("/stats/daily")
def daily_stats(days: int = 7, db: Session = Depends(get_db)):
    days = max(1, min(days, 90))

    rows = db.execute(
        text(
            """
            SELECT
                DATE(w.ts) as day,
                COUNT(*) as workouts_cnt,
                COUNT(*) FILTER (WHERE p.status = 'done') as done_cnt,
                AVG(p.calories_pred) FILTER (WHERE p.status = 'done') as avg_calories,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.calories_pred)
                    FILTER (WHERE p.status = 'done') as median_calories,
                AVG(EXTRACT(EPOCH FROM (p.processed_at - p.created_at)))
                    FILTER (WHERE p.status = 'done' AND p.processed_at IS NOT NULL) as avg_latency_sec
            FROM workouts w
            JOIN predictions p ON p.workout_id = w.workout_id
            WHERE w.ts >= NOW() - (:days || ' days')::interval
            GROUP BY DATE(w.ts)
            ORDER BY day
            """
        ),
        {"days": days},
    ).mappings().all()

    return {"items": [dict(r) for r in rows]}
