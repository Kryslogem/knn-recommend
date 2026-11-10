"""Điểm vào FastAPI.

Giai đoạn 0 chỉ có endpoint /health. Các router auth, movies, ratings,
recommendations, admin, ds và việc nạp mô hình (ModelRegistry) trong
lifespan sẽ được thêm ở giai đoạn 5 — xem PLAN.md mục 10.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Giai đoạn 5: nạp model_versions.is_active vào ModelRegistry tại đây.
    app.state.model = None
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{settings.api_prefix}/health", tags=["system"])
def health() -> dict:
    return {
        "status": "ok",
        "model_loaded": app.state.model is not None,
        "version": app.version,
    }
