"""Job huấn luyện chạy nền (thread). Mỗi lần chỉ một job; dùng chung ml.pipeline.run_training với CLI.

Dùng thread thay vì process cho đơn giản: một lần fit trên MovieLens 100K chỉ vài giây, nhưng bước đánh giá
validation khá nặng CPU nên API có thể chậm hơn trong lúc job chạy.
"""

from __future__ import annotations

import copy
import threading
import traceback

import yaml
from sqlalchemy import select

from backend.app.errors import AppError
from backend.app.models import ModelVersion, TrainingJob, utcnow
from backend.app.registry import register_bundle
from backend.app.schemas import TrainRequest
from ml.models.artifact import load_artifact
from ml.pipeline import run_training

OVERRIDES = {
    "k": ("knn", "k"), "min_k": ("knn", "min_k"), "reg_u": ("baseline", "reg_u"), "reg_i": ("baseline", "reg_i"),
    "n_epochs": ("baseline", "n_epochs"), "shrinkage": ("similarity", "shrinkage"),
    "min_support": ("similarity", "min_support"), "min_item_ratings": ("serving", "min_item_ratings"),
}


class TrainingService:
    def __init__(self, app):
        self.app = app
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def build_config(self, req: TrainRequest) -> dict:
        s = self.app.state.settings
        cfg = copy.deepcopy(yaml.safe_load(s.path(s.training_config_path).read_text(encoding="utf-8")))
        for field, (section, key) in OVERRIDES.items():
            v = getattr(req, field)
            if v is not None:
                cfg[section][key] = v
        return cfg

    def mark_interrupted(self) -> None:
        """Job còn 'running/queued' từ lần chạy trước (server tắt giữa chừng) → failed."""
        with self.app.state.SessionLocal() as db:
            for j in db.scalars(select(TrainingJob).where(TrainingJob.status.in_(["queued", "running"]))):
                j.status, j.finished_at = "failed", utcnow()
                j.log += "\nBị gián đoạn do máy chủ khởi động lại."
            db.commit()

    def start(self, user_id: int, req: TrainRequest) -> int:
        s = self.app.state.settings
        if not (s.path(s.processed_dir) / "train.csv").exists():
            raise AppError(409, "data_not_prepared", "Chưa có dữ liệu đã chia. Chạy scripts/prepare_data.py trước.")
        cfg = self.build_config(req)
        with self._lock:  # chặn đua giữa hai yêu cầu đồng thời
            with self.app.state.SessionLocal() as db:
                busy = db.scalar(select(TrainingJob.id).where(TrainingJob.status.in_(["queued", "running"])))
                if busy:
                    raise AppError(409, "job_running", f"Đang có job huấn luyện #{busy} chạy; hãy đợi job kết thúc.")
                job = TrainingJob(started_by=user_id, status="queued", config=cfg, log="")
                db.add(job)
                db.commit()
                job_id = job.id
            self._thread = threading.Thread(target=self._run, args=(job_id, cfg), daemon=True, name=f"train-{job_id}")
            self._thread.start()
        return job_id

    def _run(self, job_id: int, cfg: dict) -> None:
        s = self.app.state.settings
        SessionLocal = self.app.state.SessionLocal

        def log(msg: str) -> None:
            with SessionLocal() as db:
                j = db.get(TrainingJob, job_id)
                j.log += f"{msg}\n"
                db.commit()

        with SessionLocal() as db:
            db.get(TrainingJob, job_id).status = "running"
            db.commit()
        try:
            res = run_training(cfg, s.path(s.processed_dir), s.path(s.artifacts_dir), None, log=log)
            with SessionLocal() as db:
                row = register_bundle(db, load_artifact(res["path"]), s.path("."))
                j = db.get(TrainingJob, job_id)
                j.status, j.model_version_id, j.finished_at = "succeeded", row.id, utcnow()
                j.log += f"Hoàn tất: phiên bản {res['version']}\n"
                db.commit()
        except Exception as e:  # noqa: BLE001 - mọi lỗi phải được ghi vào job, không làm chết thread im lặng
            with SessionLocal() as db:
                j = db.get(TrainingJob, job_id)
                j.status, j.finished_at = "failed", utcnow()
                j.log += f"LỖI {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"
                db.commit()

    def wait(self, timeout: float | None = None) -> None:
        """Dùng cho test."""
        if self._thread:
            self._thread.join(timeout)


def job_json(j: TrainingJob, with_log: bool = True) -> dict:
    out = {
        "id": j.id, "status": j.status, "config": j.config, "model_version_id": j.model_version_id,
        "started_by": j.started_by, "started_at": j.started_at.isoformat(),
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
    }
    if with_log:
        out["log"] = j.log
    return out


def model_json(m: ModelVersion, detail: bool = False) -> dict:
    out = {
        "id": m.id, "version": m.version, "algorithm": m.algorithm, "is_active": m.is_active,
        "includes_app_ratings": m.includes_app_ratings, "created_at": m.created_at.isoformat(),
        "data_hash": m.data_hash, "split_hash": m.split_hash, "config": m.config,
        "metrics_val": m.metrics_val, "has_test_metrics": m.metrics_test is not None,
    }
    if detail:
        out["metrics_test"], out["artifact_path"] = m.metrics_test, m.artifact_path
    return out
