"""Đối chứng phim phổ biến (không cá nhân hóa) và danh sách cold-start.

Điểm = trung bình có làm trơn Bayes:  (n*r_bar + m*mu) / (n + m), chỉ tính từ TRAIN.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class PopularModel:
    name = "popular"

    def __init__(self, m: float = 20.0):
        if m < 0:
            raise ValueError("m phải >= 0")
        self.m = m

    def fit(self, train: pd.DataFrame) -> "PopularModel":
        self.mu = float(train["rating"].mean())
        g = train.groupby("movie_id")["rating"].agg(["sum", "count"])
        self.count = g["count"]
        self.score = (g["sum"] + self.m * self.mu) / (g["count"] + self.m)
        return self

    def predict(self, user_id: int, movie_id: int) -> float:
        """Dự đoán điểm = điểm trơn của phim (mu nếu phim lạ)."""
        return float(np.clip(self.score.get(movie_id, self.mu), 1.0, 5.0))

    def score_matrix(self, user_ids, catalog_ids) -> tuple[np.ndarray, np.ndarray]:
        row = np.clip(np.array([self.score.get(int(m), self.mu) for m in catalog_ids]), 1.0, 5.0)
        est = np.tile(row, (len(user_ids), 1))
        return est, np.zeros(est.shape, dtype=bool)

    def predict_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        est = df["movie_id"].map(self.score).fillna(self.mu).clip(1.0, 5.0)
        return pd.DataFrame({"est": est, "source": "popular", "n_neighbors": 0}, index=df.index)

    def top_n(self, n: int, exclude: set[int] | None = None) -> list[tuple[int, float]]:
        """Top-n phim theo điểm trơn; hòa → nhiều rating hơn, rồi movie_id nhỏ hơn."""
        exclude = exclude or set()
        df = pd.DataFrame({"score": self.score, "count": self.count}).rename_axis("movie_id").reset_index()
        df = df[~df["movie_id"].isin(exclude)].sort_values(
            ["score", "count", "movie_id"], ascending=[False, False, True]
        )
        return [(int(r.movie_id), float(r.score)) for r in df.head(n).itertuples()]
