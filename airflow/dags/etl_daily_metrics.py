from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime

with DAG(
    dag_id="etl_daily_metrics",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["marts", "metrics"],
) as dag:

    PostgresOperator(
        task_id="build_daily_metrics",
        postgres_conn_id="postgres_default",
        sql="""
        INSERT INTO daily_metrics (day, workouts_cnt, done_cnt, avg_calories, median_calories, avg_latency_sec)
        SELECT
            DATE(w.ts) AS day,
            COUNT(*) AS workouts_cnt,
            COUNT(*) FILTER (WHERE p.status='done') AS done_cnt,
            AVG(p.calories_pred) FILTER (WHERE p.status='done'),
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.calories_pred)
                FILTER (WHERE p.status='done'),
            AVG(EXTRACT(EPOCH FROM (p.processed_at - p.created_at)))
                FILTER (WHERE p.status='done')
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
    )
