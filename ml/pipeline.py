"""Pipeline huấn luyện dùng chung cho CLI (scripts/train.py) và backend (job nền, giai đoạn 5).

run_training(cfg, ...) fit trên TRAIN → đánh giá VALIDATION → lưu artifact có phiên bản.
Hàm này KHÔNG đọc test. Nếu đã có metrics test của đúng cấu hình/split này (từ scripts/evaluate.py),
truyền vào `test_metrics` để ghi kèm; mô hình huấn luyện trên dữ liệu khác phải để None.
"""

from __future__ import annotations

import hashlib
import json
import platform
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ml.eval.evaluate import evaluate_model
from ml.models.artifact import save_artifact
from ml.models.knn import KNNModel
from ml.models.popular import PopularModel


def knn_from_config(cfg: dict) -> KNNModel:
    b, s, k = cfg["baseline"], cfg["similarity"], cfg["knn"]
    return KNNModel(
        "baseline", k=k["k"], min_k=k["min_k"], shrinkage=s["shrinkage"], min_support=s["min_support"],
        n_epochs=b["n_epochs"], reg_u=b["reg_u"], reg_i=b["reg_i"],
    )


def config_hash(cfg: dict) -> str:
    keys = ("baseline", "similarity", "knn", "serving")
    return hashlib.sha256(json.dumps({k: cfg[k] for k in keys}, sort_keys=True).encode()).hexdigest()


def run_training(
    cfg: dict,
    processed_dir: str | Path,
    models_dir: str | Path,
    test_metrics: dict | None = None,
    log=print,
) -> dict:
    processed_dir, models_dir = Path(processed_dir), Path(models_dir)
    train = pd.read_csv(processed_dir / "train.csv")
    val = pd.read_csv(processed_dir / "validation.csv")  # cố ý không nạp test
    catalog = np.array(sorted(pd.read_csv(processed_dir / "movies.csv")["movie_id"]))
    manifest = json.loads((processed_dir / "split_manifest.json").read_text(encoding="utf-8"))
    serving = cfg["serving"]

    log("[1/3] Training KNNBaseline (ALS + Pearson-baseline + shrinkage) on the train split")
    t0 = time.time()
    knn = knn_from_config(cfg).fit(train)
    popular = PopularModel(serving["popular_bayes_m"]).fit(train)
    fit_seconds = time.time() - t0

    log("[2/3] Evaluating on the validation split")
    val_metrics, _ = evaluate_model(knn, val, train, catalog, min_item_ratings=int(serving["min_item_ratings"]))

    chash = config_hash(cfg)
    version = f"knnbaseline-{datetime.now():%Y%m%d-%H%M%S}-{chash[:8]}"
    meta = {
        "version": version,
        "algorithm": "knn_baseline",
        "params": {
            "mode": "baseline", "k": knn.k, "min_k": knn.min_k, "shrinkage": knn.shrinkage,
            "min_support": knn.min_support, "n_epochs": knn.n_epochs, "reg_u": knn.reg_u, "reg_i": knn.reg_i,
        },
        "serving": dict(serving),
        "config_hash": chash,
        "data_hash": manifest["u_data_sha256"],
        "split_hash": manifest["split_hash"],
        "trained_on": "train",
        "includes_app_ratings": False,
        "n_users": int(knn.rm.shape[0]),
        "n_items": int(knn.rm.shape[1]),
        "fit_seconds": round(fit_seconds, 3),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
    }
    metrics = {
        "validation": val_metrics,
        "test": test_metrics,
        "note": "Test metrics are present only when the configuration and split match the official evaluation (scripts/evaluate.py).",
    }
    log("[3/3] Saving the artifact")
    path = save_artifact(models_dir / version, knn, popular, meta, metrics)
    return {"version": version, "path": path, "meta": meta, "metrics": metrics}
