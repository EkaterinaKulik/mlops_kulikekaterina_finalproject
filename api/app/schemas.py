from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class WorkoutIn(BaseModel):
    user_id: str
    ts: datetime
    duration_min: float = Field(gt=0)
    distance_km: float = Field(gt=0)
    avg_hr: float | None = Field(default=None, gt=0)
    speed_kmh: float | None = Field(default=None, gt=0)

class WorkoutCreated(BaseModel):
    workout_id: UUID
    prediction_id: UUID
    status: str

class PredictionOut(BaseModel):
    workout_id: UUID
    status: str
    calories_pred: float | None = None
    model_version: str | None = None
    created_at: datetime
    processed_at: datetime | None = None
