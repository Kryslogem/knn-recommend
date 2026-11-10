"""Lưu / nạp artifact mô hình có phiên bản: artifacts/models/<version>/{model.npz, meta.json, metrics.json}.

model.npz: mu, b_u, b_i, ma trận rating train (R; mặt nạ M = R > 0 vì rating ∈ 1..5), mapping user/phim,
ma trận similarity user–user, bảng phổ biến. Residual và điểm nền được dẫn xuất lại khi nạp.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ml.models.baseline import BiasParams
from ml.models.knn import KNNModel
from ml.models.matrix import RatingMatrix
from ml.models.popular import PopularModel

ARTIFACT_FORMAT = 1


@dataclass
class Bundle:
    knn: KNNModel
    popular: PopularModel
    meta: dict
    metrics: dict
    path: Path

    @property
    def version(self) -> str:
        return self.meta["version"]

    @property
    def min_item_ratings(self) -> int:
        return int(self.meta["serving"].get("min_item_ratings", 0))


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(f"Không serialize được {type(o)}")


def save_artifact(out_dir: str | Path, knn: KNNModel, popular: PopularModel, meta: dict, metrics: dict) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)  # phiên bản là bất biến: không ghi đè
    rm = knn.rm
    arrays = dict(
        mu=np.array(knn.mu),
        user_ids=rm.user_ids,
        item_ids=rm.item_ids,
        R=rm.R,
        sim=knn.sim,
        pop_score=popular.score.reindex(rm.item_ids).to_numpy(),
        pop_count=popular.count.reindex(rm.item_ids).fillna(0).to_numpy(),
        pop_mu=np.array(popular.mu),
    )
    if knn.bias is not None:
        arrays.update(b_u=knn.bias.b_u, b_i=knn.bias.b_i, objective_history=np.array(knn.bias.objective_history))
    np.savez_compressed(out_dir / "model.npz", **arrays)
    meta = {**meta, "artifact_format": ARTIFACT_FORMAT}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return out_dir


def load_artifact(path: str | Path) -> Bundle:
    path = Path(path)
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    if meta.get("artifact_format") != ARTIFACT_FORMAT:
        raise ValueError(f"Định dạng artifact không hỗ trợ: {meta.get('artifact_format')}")
    metrics = json.loads((path / "metrics.json").read_text(encoding="utf-8"))
    with np.load(path / "model.npz") as z:
        d = {k: z[k] for k in z.files}

    p = meta["params"]
    knn = KNNModel(
        mode=p["mode"], k=p["k"], min_k=p["min_k"], shrinkage=p["shrinkage"], min_support=p["min_support"],
        n_epochs=p["n_epochs"], reg_u=p["reg_u"], reg_i=p["reg_i"],
    )
    R = d["R"]
    rm = RatingMatrix(d["user_ids"], d["item_ids"], R, R > 0)
    bias = (
        BiasParams(float(d["mu"]), d["b_u"], d["b_i"], d["objective_history"].tolist()) if "b_u" in d else None
    )
    knn.set_state(rm, float(d["mu"]), bias, d["sim"])

    pop = PopularModel(meta["serving"].get("popular_bayes_m", 20.0))
    pop.mu = float(d["pop_mu"])
    pop.score = pd.Series(d["pop_score"], index=d["item_ids"])
    pop.count = pd.Series(d["pop_count"], index=d["item_ids"])
    return Bundle(knn, pop, meta, metrics, path)
