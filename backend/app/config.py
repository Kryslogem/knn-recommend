"""Cấu hình backend, đọc từ biến môi trường (tiền tố KNN_) hoặc file .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
JWT_PLACEHOLDERS = {"", "dev-only-change-me", "change-me-to-a-long-random-string"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KNN_", env_file=ROOT / ".env", extra="ignore")

    app_name: str = "KNN Movie Recommender API"
    api_prefix: str = "/api/v1"

    database_url: str = f"sqlite:///{(ROOT / 'knn.db').as_posix()}"
    artifacts_dir: str = "artifacts/models"
    reports_dir: str = "artifacts/reports"
    processed_dir: str = "data/processed"
    training_config_path: str = "configs/model.yaml"

    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 120

    cors_origins: list[str] = ["http://localhost:5173"]

    # Tài khoản mẫu cho 3 vai trò (scripts/seed_db.py). Mật khẩu để trống → seed_db tự sinh và ghi vào .env.
    seed_admin_username: str = "admin"
    seed_admin_password: str = ""
    seed_ds_username: str = "datasci"
    seed_ds_password: str = ""
    seed_user_username: str = "demo"
    seed_user_password: str = ""

    def path(self, p: str) -> Path:
        q = Path(p)
        return q if q.is_absolute() else ROOT / q


@lru_cache
def get_settings() -> Settings:
    return Settings()
