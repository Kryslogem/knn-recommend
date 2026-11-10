"""Ma trận rating dày (user × item) + mặt nạ; 943×1682 đủ nhỏ để dùng dạng dense.

Ô chưa đánh giá có M=False và R=0 chỉ để thuận tiện tính toán; 0 KHÔNG phải rating —
mọi phép tính đều nhân với mặt nạ M.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RatingMatrix:
    user_ids: np.ndarray  # index → user_id (đã sắp xếp)
    item_ids: np.ndarray  # index → movie_id (đã sắp xếp)
    R: np.ndarray  # float64, 0 ở ô thiếu
    M: np.ndarray  # bool, True ở ô có rating

    def __post_init__(self):
        self.user_index = {int(u): i for i, u in enumerate(self.user_ids)}
        self.item_index = {int(m): i for i, m in enumerate(self.item_ids)}

    @classmethod
    def from_frame(cls, df: pd.DataFrame) -> "RatingMatrix":
        user_ids = np.sort(df["user_id"].unique())
        item_ids = np.sort(df["movie_id"].unique())
        ui = np.searchsorted(user_ids, df["user_id"].to_numpy())
        ii = np.searchsorted(item_ids, df["movie_id"].to_numpy())
        R = np.zeros((len(user_ids), len(item_ids)))
        M = np.zeros_like(R, dtype=bool)
        if M[ui, ii].any():
            raise ValueError("Trùng cặp (user, movie) trong dữ liệu huấn luyện")
        R[ui, ii] = df["rating"].to_numpy()
        M[ui, ii] = True
        return cls(user_ids, item_ids, R, M)

    @property
    def shape(self) -> tuple[int, int]:
        return self.R.shape
