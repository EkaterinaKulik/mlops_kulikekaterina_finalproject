FROM apache/airflow:2.9.3

USER airflow
RUN pip install --no-cache-dir \
    apache-airflow-providers-postgres==5.13.1 \
    psycopg2-binary==2.9.9 \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.12.txt"
