"""Phân tích lỗi theo nhóm: sai số tập trung ở đâu, KNN giúp ở đâu so với bias-only."""

from __future__ import annotations

import numpy as np
import pandas as pd

USER_BINS = ([0, 30, 100, np.inf], ["ít (<30)", "vừa (30–99)", "nhiều (≥100)"])
ITEM_BINS = ([-1, 0, 9, 49, np.inf], ["0 (không có trong train)", "1–9", "10–49", "≥50"])
NB_BINS = ([-1, 0, 5, 20, np.inf], ["0", "1–5", "6–20", ">20"])


def _group(df: pd.DataFrame, key: pd.Series, preds: dict[str, pd.DataFrame]) -> list[dict]:
    rows = []
    for g, idx in df.groupby(key, observed=True).groups.items():
        row = {"group": str(g), "n": len(idx)}
        for name, p in preds.items():
            err = p.loc[idx, "est"] - p.loc[idx, "rating"]
            row[f"rmse_{name}"] = float(np.sqrt((err**2).mean()))
            row[f"bias_{name}"] = float(err.mean())  # sai số có dấu: >0 là dự đoán cao hơn thật
        rows.append(row)
    return rows


def analyze(preds: dict[str, pd.DataFrame], main: str, train: pd.DataFrame, movies: pd.DataFrame) -> dict:
    """preds: tên mô hình → predictions (cột user_id, movie_id, rating, est, source, n_neighbors), cùng index."""
    base = preds[main]
    user_n = train.groupby("user_id").size()
    item_n = train.groupby("movie_id").size()
    df = base[["user_id", "movie_id", "rating"]].copy()
    df["user_train_n"] = df["user_id"].map(user_n).fillna(0).astype(int)
    df["item_train_n"] = df["movie_id"].map(item_n).fillna(0).astype(int)

    out = {
        "by_user_activity": _group(df, pd.cut(df["user_train_n"], *USER_BINS[:1], labels=USER_BINS[1], right=False), preds),
        "by_item_popularity": _group(df, pd.cut(df["item_train_n"], *ITEM_BINS[:1], labels=ITEM_BINS[1]), preds),
        "by_true_rating": _group(df, df["rating"], preds),
        "by_n_neighbors": _group(df, pd.cut(base["n_neighbors"], *NB_BINS[:1], labels=NB_BINS[1]), {main: base}),
    }
    err = (base["est"] - base["rating"]).abs().sort_values(ascending=False).head(10)
    title = movies.set_index("movie_id")["title"]
    out["worst_10"] = [
        {
            "user_id": int(base.loc[i, "user_id"]),
            "movie": str(title.get(base.loc[i, "movie_id"], "?")),
            "rating": int(base.loc[i, "rating"]),
            "est": round(float(base.loc[i, "est"]), 3),
            "source": str(base.loc[i, "source"]),
            "n_neighbors": int(base.loc[i, "n_neighbors"]),
            "user_train_n": int(df.loc[i, "user_train_n"]),
            "item_train_n": int(df.loc[i, "item_train_n"]),
        }
        for i in err.index
    ]
    return out
