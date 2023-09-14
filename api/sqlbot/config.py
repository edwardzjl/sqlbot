from pydantic import AnyHttpUrl, BaseSettings, PostgresDsn, RedisDsn


class Settings(BaseSettings):
    isvc_llm: AnyHttpUrl = "http://localhost:8080"
    isvc_coder_llm: AnyHttpUrl = "http://localhost:8081"
    """LLM used for generating code especially SQL"""
    log_level: str = "INFO"
    redis_om_url: RedisDsn = "redis://localhost:6379"
    warehouse_url: PostgresDsn = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
    )
    user_id_header: str = "kubeflow-userid"


settings = Settings()
