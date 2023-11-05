from typing import Optional

from pydantic import AnyHttpUrl, FilePath, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    isvc_llm: AnyHttpUrl = "http://localhost:8080"
    log_level: str = "INFO"
    redis_om_url: RedisDsn = "redis://localhost:6379"
    warehouse_url: PostgresDsn = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
    )
    custom_table_info: Optional[FilePath] = None
    """Path to a JSON file containing custom table information. If not specified, SQLBot will try to fetch the table info from the warehouse.
    JSON content should be a dict, with table names as keys and strings of table DDL as values. Few rows example could also exists in the value.
    """
    user_id_header: str = "kubeflow-userid"


settings = Settings()
