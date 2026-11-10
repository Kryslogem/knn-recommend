"""Điểm nền b_ui = mu + b_u + b_i, học bằng ALS có regularization.

Mục tiêu:  sum_{(u,i) in Train} (r_ui - mu - b_u - b_i)^2 + reg_u*sum b_u^2 + reg_i*sum b_i^2
Mỗi vòng giải ĐÚNG nghiệm đóng của từng khối (cố định b_u → cập nhật b_i, rồi ngược lại)
nên giá trị mục tiêu không tăng qua các vòng.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ml.models.matrix import RatingMatrix


@dataclass
class BiasParams:
    mu: float
    b_u: np.ndarray
    b_i: np.ndarray
    objective_history: list[float] = field(default_factory=list)

    def full(self) -> np.ndarray:
        """Ma trận điểm nền mu + b_u + b_i (user × item)."""
        return self.mu + self.b_u[:, None] + self.b_i[None, :]


def objective(rm: RatingMatrix, mu: float, b_u: np.ndarray, b_i: np.ndarray, reg_u: float, reg_i: float) -> float:
    err = (rm.R - mu - b_u[:, None] - b_i[None, :]) * rm.M
    return float((err**2).sum() + reg_u * (b_u**2).sum() + reg_i * (b_i**2).sum())


def fit_als(rm: RatingMatrix, n_epochs: int = 10, reg_u: float = 15.0, reg_i: float = 10.0) -> BiasParams:
    if n_epochs < 0 or reg_u < 0 or reg_i < 0:
        raise ValueError("n_epochs, reg_u, reg_i phải >= 0")
    M, R = rm.M, rm.R
    mu = float(R[M].mean())
    b_u = np.zeros(rm.shape[0])
    b_i = np.zeros(rm.shape[1])
    n_u = M.sum(axis=1)
    n_i = M.sum(axis=0)
    history = [objective(rm, mu, b_u, b_i, reg_u, reg_i)]
    for _ in range(n_epochs):
        b_i = ((R - mu - b_u[:, None]) * M).sum(axis=0) / (reg_i + n_i)
        b_u = ((R - mu - b_i[None, :]) * M).sum(axis=1) / (reg_u + n_u)
        history.append(objective(rm, mu, b_u, b_i, reg_u, reg_i))
    return BiasParams(mu, b_u, b_i, history)


class BiasOnlyModel:
    """Đối chứng "bias-only": dự đoán mu + b_u + b_i; user/phim lạ có bias = 0."""

    name = "bias_only"

    def __init__(self, n_epochs: int = 10, reg_u: float = 15.0, reg_i: float = 10.0):
        self.n_epochs, self.reg_u, self.reg_i = n_epochs, reg_u, reg_i

    def fit(self, train: pd.DataFrame) -> "BiasOnlyModel":
        self.rm = RatingMatrix.from_frame(train)
        self.params = fit_als(self.rm, self.n_epochs, self.reg_u, self.reg_i)
        return self

    def predict(self, user_id: int, movie_id: int) -> float:
        p = self.params
        bu = p.b_u[self.rm.user_index[user_id]] if user_id in self.rm.user_index else 0.0
        bi = p.b_i[self.rm.item_index[movie_id]] if movie_id in self.rm.item_index else 0.0
        return float(np.clip(p.mu + bu + bi, 1.0, 5.0))

    def predict_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        est = [self.predict(int(u), int(i)) for u, i in zip(df["user_id"], df["movie_id"])]
        return pd.DataFrame({"est": est, "source": "baseline", "n_neighbors": 0}, index=df.index)
