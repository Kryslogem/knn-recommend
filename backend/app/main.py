"""Điểm vào FastAPI. `create_app(settings)` tạo app độc lập (engine, registry, dịch vụ riêng) nên test dùng DB tạm."""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.config import Settings, get_settings
from backend.app.db import Base, make_engine
from backend.app.errors import register_error_handlers
from backend.app.models import ModelVersion
from backend.app.registry import ModelRegistry, register_bundle, set_active, sync_artifacts
from backend.app.routers import admin, auth, ds, movies, ratings, recommendations
from backend.app.services.recommend_service import RecommendService
from backend.app.services.training_service import TrainingService
from ml.models.artifact import load_artifact

log = logging.getLogger("knn")


def load_active_model(app: FastAPI) -> None:
    """Nạp mô hình khởi động: phiên bản is_active trong DB; nếu chưa có thì dùng artifacts/models/active.json."""
    s: Settings = app.state.settings
    models_dir, base = s.path(s.artifacts_dir), s.path(".")
    with app.state.SessionLocal() as db:
        sync_artifacts(db, models_dir, base)
        row = db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)))
        if row is None and (models_dir / "active.json").exists():
            version = json.loads((models_dir / "active.json").read_text(encoding="utf-8")).get("version")
            row = db.scalar(select(ModelVersion).where(ModelVersion.version == version))
            if row:
                set_active(db, row)
        if row is None:
            log.warning("Chưa có mô hình kích hoạt; /recommendations sẽ trả 503 cho đến khi kích hoạt.")
            return
        try:
            app.state.registry.swap(load_artifact(s.path(row.artifact_path)))
        except (OSError, ValueError, KeyError) as e:
            log.error("Không nạp được mô hình %s: %s", row.version, e)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(app.state.engine)
        app.state.trainer.mark_interrupted()
        load_active_model(app)
        yield
        app.state.engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.5.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    app.state.SessionLocal = sessionmaker(app.state.engine, expire_on_commit=False)
    app.state.registry = ModelRegistry()
    app.state.recsvc = RecommendService(app.state.registry)
    app.state.trainer = TrainingService(app)

    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )
    register_error_handlers(app)
    for r in (auth, movies, ratings, recommendations, admin, ds):
        app.include_router(r.router, prefix=settings.api_prefix)

    @app.get(f"{settings.api_prefix}/health", tags=["system"])
    def health() -> dict:
        bundle = app.state.registry.get()
        return {"status": "ok", "model_loaded": bundle is not None, "model_version": bundle.version if bundle else None, "version": app.version}

    return app


app = create_app()
