# FitBurn Rewards
MLOps system for fitness engagement and monitoring

## Business Value
FitBurn Rewards — это ML-сервис для фитнес-клубов и спортивных платформ, направленный на повышение вовлечённости и удержания пользователей.

Сервис позволяет:
- внедрять элементы геймификации в использование услуг спортивных залов и фитнес-центров с целью повышения пользовательского удержания (retention);
- предсказывать количество калорий, которые пользователь сожжёт при выполнении тренировки, и использовать это предсказание как основу для системы поощрений;
- начислять пользователям баллы за выполненные тренировки, которые могут быть использованы в рамках программ лояльности (например, обмен на мерч, скидки или бонусы);
- отслеживать и анализировать активность клиентов на уровне отдельных тренировок и агрегированных метрик;
- обеспечивать использование ML-модели в продакшене за счёт мониторинга качества предсказаний и задержек инференса.

Бизнес-эффект:
- рост user engagement,
- улучшение retention,
- data-driven управление фитнес-продуктом,
- контроль стабильности ML-модели.

## Архитектура решения

Компоненты системы:
1. ``` API service (FastAPI)  ```

Что делает:
- принимает workout-данные пользователя;
- записывает сущности в PostgreSQL:	users, workouts, predictions;
- публикует сообщение в RabbitMQ с {workout_id, prediction_id};
- предоставляет эндпоинты для получения статуса и результата предсказания;
- предоставляет эндпоинты для UI.

2. ``` Message broker (RabbitMQ) ```

Что делает:
- хранит очередь;
- обеспечивает “decoupling” между API и worker;
- позволяет масштабировать инференс увеличением числа worker-контейнеров.

3. ``` Worker service (async inference) ```

Что делает:
- слушает очередь RabbitMQ;
- для каждого сообщения: читает исходные данные тренировки из PostgreSQL (workout + user attributes при необходимости); формирует feature vector в том порядке, который сохранён в models/features.json; загружает модель из models/model.joblib (read-only volume); считает предсказание calories_pred; обновляет запись в predictions.

Модель и список фичей версионированы через артефакты (model.joblib, features.json, metrics.json).

4.  ``` Database (PostgreSQL)  ```

Слои данных:

Online tables (события и результаты):
- users — пользовательские атрибуты,
- workouts — тренировки,
- predictions — статусы и результаты инференса (pending/done/failed), latency timestamps.

Offline marts / витрины (агрегации для мониторинга и аналитики):
- daily_metrics — дневные KPI (объём тренировок, done ratio, avg/median calories, avg latency),
- leaderboard_daily — лидерборд пользователей по сожжённым калориям за день.

5. ``` Scheduler & ETL (Airflow)  ```

Что делает:

DAG etl_daily_metrics:
- агрегирует данные из workouts + predictions,
- пишет/апдейтит витрину daily_metrics.

DAG etl_leaderboard_daily:
- строит лидерборд по пользователям за день,
- пишет/апдейтит leaderboard_daily.

6. ``` Monitoring (Grafana)   ```

Как подключено:
- datasource PostgreSQL создаётся автоматически через grafana/provisioning/datasources/datasource.yml
- dashboard подгружается автоматически:
- JSON лежит в grafana/dashboards/*.json
- провайдер описан в grafana/provisioning/dashboards/dashboard.yml

7. ``` UI (Streamlit)  ```

Что делает:
- форма ввода данных тренировки → отправка в API /workouts;
- просмотр результата (polling по /predictions/{workout_id} до статуса done);
- отображение истории тренировок (recent workouts);
- отображение агрегатов (daily metrics) и бизнес-KPI.

## Быстрый старт

### Требования

- Docker 20.10+
- Docker Compose 2.0+

### Запуск сервиса

```bash
git clone <REPO_URL>
cd <REPO_DIR>
cp .env 
```

```bash
docker compose up --build
```
### Ссылки на сервисы

- API: http://localhost:8000/docs
- UI: http://localhost:8501
- Airflow: http://localhost:8088 (логин/пароль: admin/admin)
- RabbitMQ management: http://localhost:15672 (guest/guest)
- Grafana: http://localhost:3000 (admin/admin)

## Структура проекта
 ```bash
.
├── docker-compose.yml                
├── README.md                          
├── .env                              
│
├── api/                               
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── .gitkeep
│       ├── db.py                      
│       ├── main.py                    
│       ├── queue.py                   
│       ├── schemas.py                 
│       └── settings.py                
│
├── worker/                            
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── .gitkeep
│       ├── __init__.py
│       ├── db.py                      
│       ├── model_loader.py            
│       ├── settings.py                
│       └── worker.py                  
│
├── ui/                                
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── .gitkeep
│       ├── api_client.py              
│       └── streamlit_app.py           
│
├── airflow/                           
│   ├── Dockerfile
│   └── dags/
│       ├── .gitkeep
│       ├── etl_daily_metrics.py       
│       └── etl_leaderboard_daily.py   
│
├── db/                                
│   └── init/
│       ├── .gitkeep
│       ├── 001_init.sql               
│       └── 002_marts.sql              
│
├── grafana/                           
│   ├── dashboards/
│   │   ├── .gitkeep
│   │   └── FitBurn – ML Monitoring-*.json  
│   └── provisioning/
│       ├── dashboards/
│       │   ├── .gitkeep
│       │   └── dashboard.yml          
│       └── datasources/
│           ├── .gitkeep
│           └── datasource.yml         
│
├── models/                             
│   ├── .gitkeep
│   ├── features.json                  
│   ├── metrics.json                    
│   └── model.joblib                    
│
└── one-pager/
    ├── .gitkeep
    └── OPL_FitBurn.pdf                 

```
