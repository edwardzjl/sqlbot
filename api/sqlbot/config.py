from pydantic import AnyHttpUrl, BaseSettings, PostgresDsn, RedisDsn


class Settings(BaseSettings):
    inference_server_url: AnyHttpUrl = "http://localhost:8080"
    log_level: str = "INFO"
    redis_om_url: RedisDsn = "redis://localhost:6379"
    warehouse_url: PostgresDsn = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
    )


settings = Settings()
