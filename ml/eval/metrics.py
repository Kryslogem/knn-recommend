"""Chỉ số đánh giá. Phim liên quan = rating giữ lại >= 4.

Quy ước (ghi vào báo cáo):
- Precision@K luôn chia cho K, kể cả khi trả ít hơn K phim.
- Precision/Recall/NDCG chỉ tính trên người dùng có >= 1 phim liên quan (người "đủ điều kiện").
- NDCG dùng gain nhị phân: DCG = sum_{rank r=1..K} rel_r / log2(r+1); IDCG xếp min(|rel|, K) phim liên quan lên đầu.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np

RELEVANCE_THRESHOLD = 4


def rmse(y_true, y_pred) -> float:
    d = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    return float(np.sqrt((d**2).mean()))


def mae(y_true, y_pred) -> float:
    d = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    return float(np.abs(d).mean())


def ranking_metrics_for_user(ranked: Iterable[int], relevant: set[int], k: int = 10) -> tuple[float, float, float]:
    """Trả (precision@k, recall@k, ndcg@k) cho một người; `relevant` phải khác rỗng."""
    if not relevant:
        raise ValueError("relevant rỗng: người dùng không đủ điều kiện")
    top = list(ranked)[:k]
    hits = [1 if m in relevant else 0 for m in top]
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return sum(hits) / k, sum(hits) / len(relevant), dcg / idcg
