"""Chia tương tác theo từng người dùng: train / validation / test.

Quy tắc (cố định, ghi vào báo cáo):
1. Sắp rating theo (user_id, movie_id) để thứ tự đầu vào không ảnh hưởng kết quả.
2. Duyệt user theo user_id tăng dần, dùng MỘT bộ sinh `numpy.random.default_rng(seed)`
   để hoán vị rating của từng user.
3. Với user có n rating: n_test = floor(test_frac*n + 0.5), n_val = floor(val_frac*n + 0.5),
   phần còn lại vào train. Hoán vị: n_test dòng đầu → test, n_val dòng tiếp → validation.
4. Mỗi cặp (user, movie) thuộc đúng một tập. Phim chỉ có ở validation/test không bị loại;
   số lượng được ghi vào manifest và xử lý bằng fallback khi đánh giá.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from ml.data.download import sha256_file

SPLIT_NAMES = ("train", "validation", "test")
SPLIT_COLUMNS = ["user_id", "movie_id", "rating", "timestamp"]


def _round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def split_sizes(n: int, val_frac: float, test_frac: float) -> tuple[int, int, int]:
    n_test = _round_half_up(test_frac * n)
    n_val = _round_half_up(val_frac * n)
    n_train = n - n_val - n_test
    if n_train < 1:
        raise ValueError(f"User với {n} rating không còn dòng nào cho train")
    return n_train, n_val, n_test


def split_per_user(
    ratings: pd.DataFrame, seed: int, val_frac: float, test_frac: float
) -> dict[str, pd.DataFrame]:
    df = ratings[SPLIT_COLUMNS].sort_values(["user_id", "movie_id"]).reset_index(drop=True)
    rng = np.random.default_rng(seed)
    assignment = np.empty(len(df), dtype=np.int8)  # 0=train, 1=val, 2=test

    user_ids = df["user_id"].to_numpy()
    boundaries = np.flatnonzero(np.diff(user_ids)) + 1
    starts = np.concatenate(([0], boundaries))
    ends = np.concatenate((boundaries, [len(df)]))

    for start, end in zip(starts, ends):
        n = end - start
        _, n_val, n_test = split_sizes(n, val_frac, test_frac)
        perm = rng.permutation(n) + start
        assignment[perm[:n_test]] = 2
        assignment[perm[n_test : n_test + n_val]] = 1
        assignment[perm[n_test + n_val :]] = 0

    return {
        name: df[assignment == code].reset_index(drop=True)
        for code, name in enumerate(SPLIT_NAMES)
    }


def summarize_split(splits: dict[str, pd.DataFrame]) -> dict:
    train = splits["train"]
    train_items = set(train["movie_id"])
    train_users = set(train["user_id"])
    per_user_train = train.groupby("user_id").size()
    summary = {
        "rows": {k: len(v) for k, v in splits.items()},
        "users": {k: int(v["user_id"].nunique()) for k, v in splits.items()},
        "items": {k: int(v["movie_id"].nunique()) for k, v in splits.items()},
        "min_train_ratings_per_user": int(per_user_train.min()),
        "relevant_ratings_ge4": {k: int((v["rating"] >= 4).sum()) for k, v in splits.items()},
    }
    for name in ("validation", "test"):
        part = splits[name]
        cold_mask = ~part["movie_id"].isin(train_items)
        summary[f"{name}_items_not_in_train"] = int(part.loc[cold_mask, "movie_id"].nunique())
        summary[f"{name}_rows_with_item_not_in_train"] = int(cold_mask.sum())
        summary[f"{name}_users_not_in_train"] = int((~part["user_id"].isin(train_users)).sum())
    return summary


def write_split(
    splits: dict[str, pd.DataFrame], out_dir: str | Path, manifest_extra: dict
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, part in splits.items():
        path = out_dir / f"{name}.csv"
        part.to_csv(path, index=False, lineterminator="\n")
        files[name] = {"path": path.as_posix(), "sha256": sha256_file(path)}

    combined = "".join(files[n]["sha256"] for n in SPLIT_NAMES)
    manifest = {
        **manifest_extra,
        "files": files,
        "split_hash": __import__("hashlib").sha256(combined.encode()).hexdigest(),
        "summary": summarize_split(splits),
    }
    with open(out_dir / "split_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return manifest


def load_split(processed_dir: str | Path) -> dict[str, pd.DataFrame]:
    processed_dir = Path(processed_dir)
    return {name: pd.read_csv(processed_dir / f"{name}.csv") for name in SPLIT_NAMES}
