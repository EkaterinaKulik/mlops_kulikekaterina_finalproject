from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator

DEFAULT_ARGS = {"owner": "airflow", "retries": 1, "retry_delay": timedelta(minutes=1)}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS leaderboard_daily (
  day date NOT NULL,
  user_id text NOT NULL,
  total_calories double precision,
  workouts_cnt bigint NOT NULL,
  rank int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (day, user_id)
);
"""

UPSERT_SQL = """
WITH agg AS (
  SELECT
    DATE(w.ts) AS day,
    w.user_id AS user_id,
    SUM(p.calories_pred) FILTER (WHERE p.status='done') AS total_calories,
    COUNT(*) FILTER (WHERE p.status='done') AS workouts_cnt
  FROM workouts w
  JOIN predictions p ON p.workout_id = w.workout_id
  WHERE w.ts >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY DATE(w.ts), w.user_id
),
ranked AS (
  SELECT
    day,
    user_id,
    total_calories,
    workouts_cnt,
    DENSE_RANK() OVER (PARTITION BY day ORDER BY total_calories DESC NULLS LAST) AS rank
  FROM agg
)
INSERT INTO leaderboard_daily (day, user_id, total_calories, workouts_cnt, rank, created_at)
SELECT day, user_id, total_calories, workouts_cnt, rank, NOW()
FROM ranked
WHERE rank <= 10
ON CONFLICT (day, user_id) DO UPDATE SET
  total_calories = EXCLUDED.total_calories,
  workouts_cnt = EXCLUDED.workouts_cnt,
  rank = EXCLUDED.rank,
  created_at = NOW();
"""

with DAG(
    dag_id="etl_leaderboard_daily",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["marts", "leaderboard"],
) as dag:

    create_leaderboard_table = PostgresOperator(
        task_id="create_leaderboard_table",
        postgres_conn_id="postgres_default",  
        sql=CREATE_TABLE_SQL,
    )

    build_leaderboard_daily = PostgresOperator(
        task_id="build_leaderboard_daily",
        postgres_conn_id="postgres_default",  
        sql=UPSERT_SQL,
    )

    create_leaderboard_table >> build_leaderboard_daily
