import os
import time
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")


def create_workout(payload: dict) -> dict:
    r = requests.post(f"{API_BASE_URL}/workouts", json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def get_prediction(workout_id: str) -> dict:
    r = requests.get(f"{API_BASE_URL}/predictions/{workout_id}", timeout=15)
    r.raise_for_status()
    return r.json()


def wait_for_prediction(workout_id: str, timeout_sec: int = 20, poll_sec: float = 0.7) -> dict:
    start = time.time()
    last = None
    while time.time() - start < timeout_sec:
        last = get_prediction(workout_id)
        if last.get("status") in ("done", "failed"):
            return last
        time.sleep(poll_sec)
    return last or {"status": "unknown"}


def recent_workouts(limit: int = 50, user_id: str | None = None) -> dict:
    params = {"limit": limit}
    if user_id:
        params["user_id"] = user_id
    r = requests.get(f"{API_BASE_URL}/workouts/recent", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def daily_stats(days: int = 7) -> dict:
    r = requests.get(f"{API_BASE_URL}/stats/daily", params={"days": days}, timeout=20)
    r.raise_for_status()
    return r.json()
