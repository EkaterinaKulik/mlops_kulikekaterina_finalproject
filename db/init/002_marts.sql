CREATE TABLE IF NOT EXISTS daily_metrics (
    day DATE PRIMARY KEY,
    workouts_cnt INT NOT NULL,
    done_cnt INT NOT NULL,
    avg_calories DOUBLE PRECISION,
    median_calories DOUBLE PRECISION,
    avg_latency_sec DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leaderboard_daily (
    day DATE NOT NULL,
    user_id TEXT NOT NULL,
    total_calories DOUBLE PRECISION NOT NULL,
    workouts_cnt INT NOT NULL,
    rank INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (day, user_id)
);
