from pydantic import AnyHttpUrl, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    isvc_llm: AnyHttpUrl = "http://localhost:8080"
    log_level: str = "INFO"
    redis_om_url: RedisDsn = "redis://localhost:6379"
    warehouse_url: PostgresDsn = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
    )
    user_id_header: str = "kubeflow-userid"


settings = Settings()
