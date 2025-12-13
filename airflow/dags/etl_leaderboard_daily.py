from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime

with DAG(
    dag_id="etl_leaderboard_daily",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["marts", "leaderboard"],
) as dag:

    PostgresOperator(
        task_id="build_leaderboard_daily",
        postgres_conn_id="postgres_default",
        sql="""
        INSERT INTO leaderboard_daily (day, user_id, total_calories, workouts_cnt, rank)
        SELECT
            day,
            user_id,
            total_calories,
            workouts_cnt,
            RANK() OVER (PARTITION BY day ORDER BY total_calories DESC) AS rank
        FROM (
            SELECT
                DATE(w.ts) AS day,
                w.user_id,
                SUM(p.calories_pred) AS total_calories,
                COUNT(*) AS workouts_cnt
            FROM workouts w
            JOIN predictions p ON p.workout_id = w.workout_id
            WHERE p.status='done'
              AND w.ts >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(w.ts), w.user_id
        ) t
        ON CONFLICT (day, user_id) DO UPDATE SET
            total_calories = EXCLUDED.total_calories,
            workouts_cnt = EXCLUDED.workouts_cnt,
            rank = EXCLUDED.rank,
            created_at = NOW();
        """
    )
