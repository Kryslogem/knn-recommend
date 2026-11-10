"""User-based KNNBaseline và KNNBasic (tự cài).

KNNBaseline:  r^_ui = b_ui + sum_v s_uv (r_vi - b_vi) / sum_v s_uv      (v ∈ top-K, s_uv > 0, đã chấm i)
KNNBasic:     r^_ui = sum_v s_uv r_vi / sum_v s_uv                       (similarity Pearson thường)
Nếu số láng giềng thực tế < min_k → KNNBaseline trả b_ui (source="baseline"),
KNNBasic trả mu (source="baseline" = "fallback"). Kết quả chặn trong [1, 5].
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.models.baseline import fit_als
from ml.models.matrix import RatingMatrix
from ml.models.similarity import pearson, pearson_baseline


def neighbor_aggregate(
    sim_row: np.ndarray, V: np.ndarray, M: np.ndarray, item_idx: np.ndarray, k: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Với mỗi phim trong `item_idx`, lấy tối đa k láng giềng (s>0, đã chấm phim đó).

    Trả (agg, n_neighbors, weight_sum) với agg = trung bình có trọng số của V trên láng giềng.
    Hàm dùng chung cho dự đoán thường và cho fold-in hồ sơ ngoài train (giai đoạn 4).
    """
    pos = sim_row > 0
    W = np.where(M[:, item_idx] & pos[:, None], sim_row[:, None], 0.0)  # (n_users, n_items)
    if k < W.shape[0]:
        top = np.argpartition(-W, k - 1, axis=0)[:k]
        keep = np.zeros_like(W, dtype=bool)
        np.put_along_axis(keep, top, True, axis=0)
        W = np.where(keep, W, 0.0)
    n_nb = (W > 0).sum(axis=0)
    wsum = W.sum(axis=0)
    num = (W * V[:, item_idx]).sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        agg = np.where(wsum > 0, num / wsum, 0.0)
    return agg, n_nb, wsum


class KNNModel:
    def __init__(
        self,
        mode: str = "baseline",
        k: int = 40,
        min_k: int = 1,
        shrinkage: float = 100.0,
        min_support: int = 1,
        n_epochs: int = 10,
        reg_u: float = 15.0,
        reg_i: float = 10.0,
    ):
        if mode not in ("baseline", "basic"):
            raise ValueError("mode phải là 'baseline' hoặc 'basic'")
        if k < 1 or min_k < 1 or shrinkage < 0 or min_support < 1:
            raise ValueError("k, min_k, min_support phải >= 1 và shrinkage >= 0")
        self.mode, self.k, self.min_k = mode, k, min_k
        self.shrinkage, self.min_support = shrinkage, min_support
        self.n_epochs, self.reg_u, self.reg_i = n_epochs, reg_u, reg_i
        self.name = "knn_baseline" if mode == "baseline" else "knn_basic"

    def fit(self, train: pd.DataFrame) -> "KNNModel":
        rm = RatingMatrix.from_frame(train)
        mu = float(rm.R[rm.M].mean())
        bias = fit_als(rm, self.n_epochs, self.reg_u, self.reg_i) if self.mode == "baseline" else None
        self.set_state(rm, mu, bias)
        if self.mode == "baseline":
            self.sim = pearson_baseline(self.V, rm.M, self.shrinkage, self.min_support)
        else:
            self.sim = pearson(rm.R, rm.M, self.shrinkage, self.min_support)
        return self

    def set_state(self, rm: RatingMatrix, mu: float, bias, sim: np.ndarray | None = None) -> "KNNModel":
        """Gán trạng thái đã học (dùng khi fit hoặc nạp từ artifact) và dẫn xuất điểm nền + residual."""
        self.rm, self.mu, self.bias = rm, mu, bias
        if self.mode == "baseline":
            self.base = bias.full()
            self.V = (rm.R - self.base) * rm.M  # residual e_vi
        else:
            self.base = np.full(rm.shape, mu)
            self.V = rm.R * rm.M
        if sim is not None:
            self.sim = sim
        return self

    def _predict_user_items(self, uidx: int, item_idx: np.ndarray):
        agg, n_nb, _ = neighbor_aggregate(self.sim[uidx], self.V, self.rm.M, item_idx, self.k)
        base = self.base[uidx, item_idx]
        use_knn = n_nb >= self.min_k
        if self.mode == "baseline":
            est = np.where(use_knn, base + agg, base)
        else:
            est = np.where(use_knn, agg, self.mu)
        return np.clip(est, 1.0, 5.0), use_knn, n_nb

    def predict_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """Dự đoán cho từng dòng (user_id, movie_id); trả est, source, n_neighbors (cùng index)."""
        est = np.full(len(df), np.nan)
        source = np.full(len(df), "baseline", dtype=object)
        n_nb = np.zeros(len(df), dtype=int)
        pos_of = {idx: p for p, idx in enumerate(df.index)}
        rm = self.rm
        for uid, sub in df.groupby("user_id"):
            positions = np.array([pos_of[i] for i in sub.index])
            mids = sub["movie_id"].to_numpy()
            known = np.array([int(m) in rm.item_index for m in mids])
            uidx = rm.user_index.get(int(uid))
            bu = self.bias.b_u[uidx] if (self.bias is not None and uidx is not None) else 0.0
            # mặc định (user/phim lạ): mu + bias đã biết
            bi = np.array([self.bias.b_i[rm.item_index[int(m)]] if (self.bias is not None and k_) else 0.0
                           for m, k_ in zip(mids, known)])
            est[positions] = np.clip(self.mu + bu + bi if self.mode == "baseline" else self.mu, 1.0, 5.0)
            if uidx is None or not known.any():
                continue
            iidx = np.array([rm.item_index[int(m)] for m in mids[known]])
            e, use_knn, nn = self._predict_user_items(uidx, iidx)
            est[positions[known]] = e
            source[positions[known]] = np.where(use_knn, "knn", "baseline")
            n_nb[positions[known]] = nn
        return pd.DataFrame({"est": est, "source": source, "n_neighbors": n_nb}, index=df.index)

    def score_matrix(self, user_ids, catalog_ids) -> tuple[np.ndarray, np.ndarray]:
        """Điểm dự đoán (users × catalog) và cờ "dùng KNN". Phim/người lạ dùng điểm nền."""
        rm = self.rm
        catalog_ids = np.asarray(catalog_ids)
        known = np.array([int(m) in rm.item_index for m in catalog_ids])
        iidx = np.array([rm.item_index[int(m)] for m in catalog_ids[known]], dtype=int)
        bi = np.zeros(len(catalog_ids))
        if self.bias is not None:
            bi[known] = self.bias.b_i[iidx]
        est = np.empty((len(user_ids), len(catalog_ids)))
        used = np.zeros(est.shape, dtype=bool)
        for r, uid in enumerate(user_ids):
            uidx = rm.user_index.get(int(uid))
            bu = self.bias.b_u[uidx] if (self.bias is not None and uidx is not None) else 0.0
            row = np.full(len(catalog_ids), self.mu) if self.mode == "basic" else self.mu + bu + bi
            est[r] = np.clip(row, 1.0, 5.0)
            if uidx is not None and known.any():
                e, use_knn, _ = self._predict_user_items(uidx, iidx)
                est[r, known] = e
                used[r, known] = use_knn
        return est, used

    def predict(self, user_id: int, movie_id: int) -> dict:
        row = self.predict_frame(pd.DataFrame({"user_id": [user_id], "movie_id": [movie_id]})).iloc[0]
        return {"est": float(row["est"]), "source": row["source"], "n_neighbors": int(row["n_neighbors"])}
