"""Đánh giá một mô hình trên một tập giữ lại (validation hoặc test).

Mọi mô hình dùng chung: split, tập ứng viên, quy tắc fallback.
Tập ứng viên của người u = toàn bộ danh mục TRỪ phim u đã chấm trong train
(và trừ phim u đã chấm trong validation khi đánh giá TEST, vì chưa biết sở thích đó).
Ngưỡng `min_item_ratings` (tùy chọn): chỉ xếp hạng phim có >= ngưỡng rating TRONG TRAIN.
Ngưỡng chỉ ảnh hưởng xếp hạng Top-N, không ảnh hưởng MAE/RMSE.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.eval.metrics import RELEVANCE_THRESHOLD, mae, ranking_metrics_for_user, rmse


def _items_by_user(*frames: pd.DataFrame) -> dict[int, set[int]]:
    allf = pd.concat(frames)
    return {int(u): set(map(int, g["movie_id"])) for u, g in allf.groupby("user_id")}


def allowed_mask(catalog_ids, item_counts: pd.Series | None, min_item_ratings: int) -> np.ndarray:
    """True cho phim đủ điều kiện được xếp hạng (số rating train >= ngưỡng)."""
    catalog_ids = np.asarray(catalog_ids)
    if not min_item_ratings or item_counts is None:
        return np.ones(len(catalog_ids), dtype=bool)
    return item_counts.reindex(catalog_ids).fillna(0).to_numpy() >= min_item_ratings


def rank_from_scores(est, users, catalog_ids, exclude_by_user, k: int = 10, allowed=None) -> dict[int, np.ndarray]:
    """Top-k movie_id từ ma trận điểm. Hòa điểm → movie_id nhỏ trước (catalog phải tăng dần).

    Trả ít hơn k phim nếu số ứng viên hợp lệ không đủ k.
    """
    catalog_ids = np.asarray(catalog_ids)
    assert (np.diff(catalog_ids) > 0).all(), "catalog_ids phải sắp tăng dần"
    pos = {int(m): i for i, m in enumerate(catalog_ids)}
    out = {}
    for r, u in enumerate(users):
        row = est[r].astype(float).copy()
        if allowed is not None:
            row[~allowed] = -np.inf
        ex = [pos[m] for m in exclude_by_user.get(int(u), ()) if m in pos]
        row[ex] = -np.inf
        order = np.argsort(-row, kind="stable")[:k]
        out[int(u)] = catalog_ids[order[np.isfinite(row[order])]]
    return out


def top_k_lists(model, users, catalog_ids, exclude_by_user, k: int = 10, allowed=None) -> dict[int, np.ndarray]:
    est, _ = model.score_matrix(users, np.asarray(catalog_ids))
    return rank_from_scores(est, users, catalog_ids, exclude_by_user, k, allowed)


def ranking_block(tops: dict[int, np.ndarray], relevant_by_user: dict, n_catalog: int, k: int, suffix: str = "") -> dict:
    users = sorted(relevant_by_user)
    vals = np.array([ranking_metrics_for_user(tops[u], relevant_by_user[u], k) for u in users])
    shown = {int(m) for t in tops.values() for m in t}
    return {
        f"precision@{k}{suffix}": float(vals[:, 0].mean()),
        f"recall@{k}{suffix}": float(vals[:, 1].mean()),
        f"ndcg@{k}{suffix}": float(vals[:, 2].mean()),
        f"catalog_coverage{suffix}": len(shown) / n_catalog,
    }


def relevant_items(heldout: pd.DataFrame) -> dict[int, set[int]]:
    rel = heldout[heldout["rating"] >= RELEVANCE_THRESHOLD]
    return {int(u): set(map(int, g["movie_id"])) for u, g in rel.groupby("user_id")}


def evaluate_model(
    model,
    heldout: pd.DataFrame,
    train: pd.DataFrame,
    catalog_ids,
    extra_exclude: pd.DataFrame | None = None,
    k: int = 10,
    min_item_ratings: int = 0,
) -> tuple[dict, pd.DataFrame]:
    """Trả (metrics, predictions). predictions = heldout + est/source/n_neighbors.

    Chỉ số xếp hạng không hậu tố = không lọc ngưỡng; nếu min_item_ratings > 0 có thêm
    các chỉ số hậu tố "_min{N}" cho danh sách đã lọc.
    """
    catalog_ids = np.asarray(catalog_ids)
    pred = model.predict_frame(heldout)
    preds = heldout.join(pred)
    is_knn = preds["source"] == "knn"
    metrics = {
        "n_pairs": len(preds),
        "rmse": rmse(preds["rating"], preds["est"]),
        "mae": mae(preds["rating"], preds["est"]),
        "rmse_knn_supported": rmse(preds.loc[is_knn, "rating"], preds.loc[is_knn, "est"]) if is_knn.any() else float("nan"),
        "prediction_coverage_knn": float(is_knn.mean()),
        "fallback_rate": float(1 - is_knn.mean()),
    }

    relevant_by_user = relevant_items(heldout)
    users = sorted(relevant_by_user)
    exclude = _items_by_user(train, *([extra_exclude] if extra_exclude is not None else []))
    est, _ = model.score_matrix(users, catalog_ids)
    metrics.update(ranking_block(rank_from_scores(est, users, catalog_ids, exclude, k), relevant_by_user, len(catalog_ids), k))
    metrics["n_eligible_users"] = len(users)
    if min_item_ratings:
        counts = train.groupby("movie_id").size()
        allowed = allowed_mask(catalog_ids, counts, min_item_ratings)
        tops = rank_from_scores(est, users, catalog_ids, exclude, k, allowed)
        metrics.update(ranking_block(tops, relevant_by_user, len(catalog_ids), k, suffix=f"_min{min_item_ratings}"))
    return metrics, preds
