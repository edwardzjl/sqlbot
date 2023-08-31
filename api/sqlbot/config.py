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
    schema_file: str = "/etc/sqlbot/schema.json"
    """JSON file containing table names and their descriptions"""


settings = Settings()
