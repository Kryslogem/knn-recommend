"""Cấu hình backend, đọc từ biến môi trường (tiền tố KNN_) hoặc file .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KNN_", env_file=".env", extra="ignore")

    app_name: str = "KNN Movie Recommender API"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./knn.db"
    artifacts_dir: str = "artifacts/models"

    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 120

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
