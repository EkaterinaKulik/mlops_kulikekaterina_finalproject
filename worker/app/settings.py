from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    rabbitmq_url: str
    queue_name: str = "workouts"
    model_version: str = "stub-v0"

settings = Settings()
