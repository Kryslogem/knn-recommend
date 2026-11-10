"""Suy luận cho người dùng NGOÀI train (người dùng web) — "fold-in".

Mô hình đã fit không có hàng nào cho họ, nên `predict(user_id, ...)` không cá nhân hóa được.
Mỗi lần đề xuất ta dựng lại hồ sơ truy vấn từ các điểm hiện hành:
  1. Bỏ phim mô hình không biết (ghi số lượng).
  2. Giữ nguyên b_i đã học; ước lượng bias hồ sơ  b_q = sum(r - mu - b_i) / (reg_u + |P|).
  3. Residual e_qi = r - mu - b_q - b_i; similarity (Pearson-baseline + shrinkage) với MỌI user train.
  4. Dự đoán KNN cho các phim ứng viên; loại phim đã chấm; xếp hạng; lấy Top-N.
Hồ sơ KHÔNG được thêm vào cộng đồng tham chiếu; điều đó chỉ xảy ra qua lần huấn luyện có phiên bản.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np

from ml.models.knn import KNNModel, neighbor_aggregate
from ml.models.popular import PopularModel
from ml.models.similarity import profile_similarity_baseline, profile_similarity_pearson


@dataclass
class FoldIn:
    item_idx: np.ndarray  # chỉ số (trong mô hình) các phim đã chấm mà mô hình biết
    ratings: np.ndarray
    dropped_ids: list[int]  # phim đã chấm nhưng mô hình không biết
    b_q: float
    mask: np.ndarray  # (n_items,) bool
    sim: np.ndarray  # (n_users,) similarity với user train

    @property
    def size(self) -> int:
        return len(self.item_idx)


def validate_ratings(ratings: Mapping[int, int]) -> dict[int, int]:
    out = {}
    for m, r in ratings.items():
        if isinstance(r, bool) or not isinstance(r, (int, np.integer)) or not 1 <= int(r) <= 5:
            raise ValueError(f"Invalid rating for film {m}: {r!r} (must be an integer from 1 to 5)")
        out[int(m)] = int(r)
    return out


def fold_in(
    model: KNNModel,
    ratings: Mapping[int, int],
    exclude_user_id: int | None = None,
    bias_override: float | None = None,
) -> FoldIn:
    """Dựng hồ sơ truy vấn. `exclude_user_id` (chỉ dùng khi kiểm thử với user train) bỏ chính họ khỏi láng giềng;
    `bias_override` thay b_q bằng giá trị cho trước (kiểm thử tính đúng của phần similarity/dự đoán)."""
    ratings = validate_ratings(ratings)
    rm = model.rm
    known = [(rm.item_index[m], r) for m, r in sorted(ratings.items()) if m in rm.item_index]
    dropped = [m for m in sorted(ratings) if m not in rm.item_index]
    idx = np.array([i for i, _ in known], dtype=int)
    r = np.array([x for _, x in known], dtype=float)

    mask = np.zeros(rm.shape[1], dtype=bool)
    mask[idx] = True
    b_q = 0.0
    sim = np.zeros(rm.shape[0])
    if len(idx):
        vec = np.zeros(rm.shape[1])
        if model.mode == "baseline":
            b_i = model.bias.b_i[idx]
            b_q = float((r - model.mu - b_i).sum() / (model.reg_u + len(idx))) if bias_override is None else float(bias_override)
            vec[idx] = r - model.mu - b_q - b_i
            sim = profile_similarity_baseline(model.V, rm.M, vec, mask, model.shrinkage, model.min_support)
        else:
            vec[idx] = r
            sim = profile_similarity_pearson(rm.R, rm.M, vec, mask, model.shrinkage, model.min_support)
    if exclude_user_id is not None and exclude_user_id in rm.user_index:
        sim[rm.user_index[exclude_user_id]] = 0.0
    return FoldIn(idx, r, dropped, b_q, mask, sim)


def neighbors_for_item(model: KNNModel, fi: FoldIn, item_index: int, top: int = 3) -> list[dict]:
    """Láng giềng đóng góp nhiều nhất cho một phim (ẩn danh): similarity, điểm họ chấm, số phim chung."""
    w = np.where(model.rm.M[:, item_index] & (fi.sim > 0), fi.sim, 0.0)
    if model.k < len(w):
        keep = np.argpartition(-w, model.k - 1)[: model.k]
        w2 = np.zeros_like(w)
        w2[keep] = w[keep]
        w = w2
    order = np.lexsort((np.arange(len(w)), -w))[:top]
    return [
        {
            "label": f"Viewer #{n + 1}",
            "similarity": round(float(w[v]), 4),
            "rating": int(model.rm.R[v, item_index]),
            "common_items": int((model.rm.M[v] & fi.mask).sum()),
        }
        for n, v in enumerate(order)
        if w[v] > 0
    ]


def recommend(
    model: KNNModel,
    popular: PopularModel,
    ratings: Mapping[int, int],
    n: int = 10,
    min_item_ratings: int = 0,
    exclude_ids: Iterable[int] = (),
    allowed_ids: Iterable[int] | None = None,
    with_neighbors: bool = True,
    exclude_user_id: int | None = None,
    bias_override: float | None = None,
) -> dict:
    """Top-N cho một hồ sơ. Không bao giờ chứa phim đã chấm.

    source: "knn" (đủ >= min_k láng giềng) | "baseline" (thiếu láng giềng, dùng mu+b_q+b_i) |
            "popular" (hồ sơ rỗng/không có phim mô hình biết).
    """
    if n < 1:
        raise ValueError("n phải >= 1")
    rm = model.rm
    fi = fold_in(model, ratings, exclude_user_id, bias_override)
    rated = {int(m) for m in ratings}
    blocked = rated | {int(m) for m in exclude_ids}
    allowed = None if allowed_ids is None else {int(m) for m in allowed_ids}
    counts = rm.M.sum(axis=0)

    ok = (counts >= min_item_ratings) & ~np.isin(rm.item_ids, list(blocked))
    if allowed is not None:
        ok &= np.isin(rm.item_ids, list(allowed))
    cand = np.flatnonzero(ok)
    message = None

    if fi.size == 0:
        message = "No usable ratings yet, so these are popular films. Rate a few films to get personalized recommendations."
        excl = {int(m) for m in rm.item_ids[~ok]}
        items = [
            {
                "movie_id": m, "predicted_rating": round(s, 4), "source": "popular", "n_neighbors": 0,
                "breakdown": None, "neighbors": [],
            }
            for m, s in popular.top_n(n, excl)
        ]
    else:
        agg, nn, _ = neighbor_aggregate(fi.sim, model.V, rm.M, cand, model.k)
        if model.mode == "baseline":
            base = model.mu + fi.b_q + model.bias.b_i[cand]
        else:
            base = np.full(len(cand), model.mu)
        use_knn = nn >= model.min_k
        if model.mode == "baseline":
            raw = np.where(use_knn, base + agg, base)
        else:
            raw = np.where(use_knn, agg, model.mu)
        est = np.clip(raw, 1.0, 5.0)
        mids = rm.item_ids[cand]
        order = np.lexsort((mids, -nn, -est))[:n]  # điểm ↓, số láng giềng ↓, movie_id ↑ (tái lập)
        items = []
        for o in order:
            neighbor_term = float(agg[o]) if use_knn[o] else 0.0
            items.append(
                {
                    "movie_id": int(mids[o]),
                    "predicted_rating": round(float(est[o]), 4),
                    "source": "knn" if use_knn[o] else "baseline",
                    "n_neighbors": int(nn[o]),
                    "breakdown": {
                        "mu": model.mu,
                        "b_user": fi.b_q,
                        "b_item": float(model.bias.b_i[cand[o]]) if model.mode == "baseline" else 0.0,
                        "neighbor_term": neighbor_term,
                        "clipped": bool(raw[o] != est[o]),
                    },
                    "neighbors": neighbors_for_item(model, fi, int(cand[o])) if (with_neighbors and use_knn[o]) else [],
                }
            )
        if len(items) < n:
            message = f"Only {len(items)} films satisfy the filters and threshold (requested {n})."

    summary = {s: sum(1 for it in items if it["source"] == s) for s in ("knn", "baseline", "popular")}
    return {
        "profile_size": fi.size,
        "dropped_unknown_items": fi.dropped_ids,
        "n_candidates": int(len(cand)),
        "source_summary": summary,
        "items": items,
        "message": message,
    }
