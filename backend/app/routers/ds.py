"""Data scientist functions: data, training, model versions, evaluation. role=data_scientist only."""

import csv
import json
import math
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.errors import AppError
from backend.app.models import ModelVersion, TrainingJob, User
from backend.app.registry import set_active, sync_artifacts
from backend.app.schemas import TrainRequest
from backend.app.security import require_role
from backend.app.services.training_service import job_json, model_json
from ml.models.artifact import load_artifact

router = APIRouter(prefix="/ds", tags=["data-scientist"], dependencies=[Depends(require_role("data_scientist"))])
DS = Depends(require_role("data_scientist"))


def _clean(o):
    """NaN/Inf are invalid in standard JSON, so they become null."""
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def _read_json(path: Path, hint: str):
    if not path.exists():
        raise AppError(404, "report_missing", f"Report not available yet ({path.name}). {hint}")
    return _clean(json.loads(path.read_text(encoding="utf-8")))


def _reports(request: Request) -> Path:
    s = request.app.state.settings
    return s.path(s.reports_dir)


@router.get("/data/report")
def data_report(request: Request):
    return _read_json(_reports(request) / "data_report.json", "Run scripts/prepare_data.py.")


@router.get("/data/split")
def data_split(request: Request):
    s = request.app.state.settings
    return _read_json(s.path(s.processed_dir) / "split_manifest.json", "Run scripts/prepare_data.py.")


@router.post("/training-jobs", status_code=202)
def create_job(body: TrainRequest, request: Request, user: User = DS):
    job_id = request.app.state.trainer.start(user.id, body)
    return {"id": job_id, "status": "queued"}


@router.get("/training-jobs")
def list_jobs(db: Session = Depends(get_db)):
    return {"items": [job_json(j, with_log=False) for j in db.scalars(select(TrainingJob).order_by(TrainingJob.id.desc()).limit(50))]}


@router.get("/training-jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(TrainingJob, job_id)
    if j is None:
        raise AppError(404, "job_not_found", "Training job not found")
    return job_json(j)


@router.get("/models")
def list_models(request: Request, db: Session = Depends(get_db)):
    s = request.app.state.settings
    sync_artifacts(db, s.path(s.artifacts_dir), s.path("."))  # includes models trained from the CLI
    return {"items": [model_json(m) for m in db.scalars(select(ModelVersion).order_by(ModelVersion.id.desc()))]}


@router.get("/models/{model_id}")
def get_model(model_id: int, db: Session = Depends(get_db)):
    m = db.get(ModelVersion, model_id)
    if m is None:
        raise AppError(404, "model_not_found", "Model version not found")
    return model_json(m, detail=True)


@router.post("/models/{model_id}/activate")
def activate(model_id: int, request: Request, db: Session = Depends(get_db)):
    """Hot-swap: load and validate the artifact FIRST, then replace the serving model. No restart needed."""
    m = db.get(ModelVersion, model_id)
    if m is None:
        raise AppError(404, "model_not_found", "Model version not found")
    s = request.app.state.settings
    try:
        bundle = load_artifact(s.path(m.artifact_path))
    except (OSError, ValueError, KeyError) as e:
        raise AppError(409, "artifact_unavailable", f"Could not load the artifact: {e}") from None
    request.app.state.registry.swap(bundle)
    set_active(db, m)
    request.app.state.recsvc.clear()
    (s.path(s.artifacts_dir) / "active.json").write_text(json.dumps({"version": m.version}), encoding="utf-8")
    return model_json(m)


@router.get("/evaluation/comparison")
def comparison(request: Request):
    return _read_json(_reports(request) / "comparison.json", "Run scripts/evaluate.py.")


@router.get("/evaluation/tuning")
def tuning(request: Request):
    p = _reports(request) / "tuning.csv"
    if not p.exists():
        raise AppError(404, "report_missing", "tuning.csv is not available yet. Run scripts/tune.py.")
    with open(p, encoding="utf-8", newline="") as f:
        rows = [{k: (float(v) if v not in ("", None) and k != "" else None) for k, v in r.items()} for r in csv.DictReader(f)]
    return {"items": _clean(rows)}


@router.get("/evaluation/errors")
def errors(request: Request):
    return _read_json(_reports(request) / "error_analysis.json", "Run scripts/evaluate.py.")
