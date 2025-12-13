CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  age INT,
  sex TEXT,
  height_cm DOUBLE PRECISION,
  weight_kg DOUBLE PRECISION,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workouts (
  workout_id UUID PRIMARY KEY,
  user_id TEXT REFERENCES users(user_id),
  ts TIMESTAMP NOT NULL,
  duration_min DOUBLE PRECISION,
  distance_km DOUBLE PRECISION,
  avg_hr DOUBLE PRECISION,
  speed_kmh DOUBLE PRECISION,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
  prediction_id UUID PRIMARY KEY,
  workout_id UUID REFERENCES workouts(workout_id),
  status TEXT NOT NULL,
  calories_pred DOUBLE PRECISION,
  model_version TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  processed_at TIMESTAMP
);
