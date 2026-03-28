from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        database_url (str): SQLAlchemy database URL for MySQL.
        jwt_secret (str): Secret key for signing JWT tokens.
        jwt_algorithm (str): JWT algorithm name.
        jwt_expire_hours (int): Token expiration in hours.
        cors_origins (List[str]): Allowed CORS origins.
    """

    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/blog_platform?charset=utf8mb4"
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    cors_origins: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_prefix="BLOG_",
        env_file="backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings.

    Returns:
        Settings: Cached settings instance.
    """

    return Settings()
