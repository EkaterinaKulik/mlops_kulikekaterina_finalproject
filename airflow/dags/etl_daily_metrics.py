from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator

DEFAULT_ARGS = {"owner": "airflow", "retries": 1, "retry_delay": timedelta(minutes=1)}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_metrics (
  day date PRIMARY KEY,
  workouts_cnt bigint NOT NULL,
  done_cnt bigint NOT NULL,
  avg_calories double precision,
  median_calories double precision,
  avg_latency_sec double precision,
  created_at timestamptz NOT NULL DEFAULT now()
);
"""

UPSERT_SQL = """
INSERT INTO daily_metrics (day, workouts_cnt, done_cnt, avg_calories, median_calories, avg_latency_sec)
SELECT
    DATE(w.ts) AS day,
    COUNT(*) AS workouts_cnt,
    COUNT(*) FILTER (WHERE p.status='done') AS done_cnt,
    AVG(p.calories_pred) FILTER (WHERE p.status='done') AS avg_calories,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.calories_pred)
        FILTER (WHERE p.status='done') AS median_calories,
    AVG(EXTRACT(EPOCH FROM (p.processed_at - p.created_at)))
        FILTER (WHERE p.status='done') AS avg_latency_sec
FROM workouts w
JOIN predictions p ON p.workout_id = w.workout_id
WHERE w.ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(w.ts)
ON CONFLICT (day) DO UPDATE SET
    workouts_cnt = EXCLUDED.workouts_cnt,
    done_cnt = EXCLUDED.done_cnt,
    avg_calories = EXCLUDED.avg_calories,
    median_calories = EXCLUDED.median_calories,
    avg_latency_sec = EXCLUDED.avg_latency_sec,
    created_at = NOW();
"""

with DAG(
    dag_id="etl_daily_metrics",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["marts", "metrics"],
) as dag:

    create_daily_metrics_table = PostgresOperator(
        task_id="create_daily_metrics_table",
        postgres_conn_id="postgres_default", 
        sql=CREATE_TABLE_SQL,
    )

    build_daily_metrics = PostgresOperator(
        task_id="build_daily_metrics",
        postgres_conn_id="postgres_default",  
        sql=UPSERT_SQL,
    )

    create_daily_metrics_table >> build_daily_metrics

