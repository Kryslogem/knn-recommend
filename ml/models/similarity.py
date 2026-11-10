"""Độ tương đồng user–user, vector hóa bằng nhân ma trận.

Với E (residual, 0 ở ô thiếu) và M (mặt nạ), trên tập phim chung I_uv:
    tử số        = (E @ E.T)[u,v]
    |I_uv|       = (M @ M.T)[u,v]
    sum e_u^2    = ((E*E) @ M.T)[u,v]        (chỉ cộng trên phim v cũng đã chấm)
Pearson-baseline:  rho = tử số / sqrt(sum e_u^2 * sum e_v^2)
Shrinkage:         s = (|I_uv|-1) / (|I_uv|-1+shrinkage) * rho
Quy ước: cần |I_uv| >= max(min_support, 2); ngược lại s = 0. Mẫu số 0 → s = 0. Đường chéo = 0.
"""

from __future__ import annotations

import numpy as np


def _shrink(rho: np.ndarray, n_common: np.ndarray, shrinkage: float, min_support: int) -> np.ndarray:
    """Áp shrinkage và ngưỡng phim chung; dùng cho cả ma trận lẫn vector (hồ sơ ngoài train)."""
    denom = n_common - 1 + shrinkage
    with np.errstate(divide="ignore", invalid="ignore"):
        factor = np.where(denom > 0, (n_common - 1) / denom, 0.0)
    sim = np.where(n_common < max(min_support, 2), 0.0, rho * factor)
    return np.clip(sim, -1.0, 1.0)  # chặn sai số làm tròn


def _finish(rho: np.ndarray, n_common: np.ndarray, shrinkage: float, min_support: int) -> np.ndarray:
    sim = _shrink(rho, n_common, shrinkage, min_support)
    np.fill_diagonal(sim, 0.0)
    return sim


def profile_similarity_baseline(
    E: np.ndarray, M: np.ndarray, e_q: np.ndarray, m_q: np.ndarray, shrinkage: float, min_support: int
) -> np.ndarray:
    """Similarity Pearson-baseline giữa MỘT hồ sơ truy vấn (residual e_q, mặt nạ m_q) và mọi user train.

    Cùng công thức với `pearson_baseline` nhưng một hàng: dùng cho người dùng ngoài train (fold-in).
    """
    Mf, mq = M.astype(float), m_q.astype(float)
    num = E @ e_q
    n = Mf @ mq
    den = np.sqrt(((E * E) @ mq) * (Mf @ (e_q * e_q)))
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = np.where(den > 0, num / den, 0.0)
    return _shrink(rho, n, shrinkage, min_support)


def profile_similarity_pearson(
    R: np.ndarray, M: np.ndarray, r_q: np.ndarray, m_q: np.ndarray, shrinkage: float, min_support: int
) -> np.ndarray:
    """Một hàng của `pearson` (KNNBasic) cho hồ sơ truy vấn."""
    Mf, mq = M.astype(float), m_q.astype(float)
    Rm, rq = R * M, r_q * m_q
    n = Mf @ mq
    S_v, S_q = Rm @ mq, Mf @ rq
    with np.errstate(divide="ignore", invalid="ignore"):
        num = Rm @ rq - S_v * S_q / n
        den = np.sqrt(((Rm * Rm) @ mq - S_v**2 / n) * (Mf @ (rq * rq) - S_q**2 / n))
        rho = np.where((n > 0) & (den > 1e-12), num / den, 0.0)
    return _shrink(rho, n, shrinkage, min_support)


def pearson_baseline(E: np.ndarray, M: np.ndarray, shrinkage: float = 100.0, min_support: int = 1) -> np.ndarray:
    """Pearson trên residual so với điểm nền. E phải bằng 0 ở ô thiếu."""
    Mf = M.astype(float)
    num = E @ E.T
    n_common = Mf @ Mf.T
    sq = (E * E) @ Mf.T  # sq[u,v] = sum_{i in I_uv} e_ui^2
    den = np.sqrt(sq * sq.T)
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = np.where(den > 0, num / den, 0.0)
    return _finish(rho, n_common, shrinkage, min_support)


def pearson(R: np.ndarray, M: np.ndarray, shrinkage: float = 0.0, min_support: int = 1) -> np.ndarray:
    """Pearson thường (cho KNNBasic): trung tâm hóa theo trung bình của mỗi user TRÊN phim chung."""
    Rm = R * M
    Mf = M.astype(float)
    n = Mf @ Mf.T
    S = Rm @ Mf.T  # S[u,v] = sum_{i in I_uv} r_ui
    cross = Rm @ Rm.T  # sum r_ui r_vi
    sq = (Rm * Rm) @ Mf.T  # sum_{i in I_uv} r_ui^2
    with np.errstate(divide="ignore", invalid="ignore"):
        num = cross - S * S.T / n
        var_u = sq - S * S / n
        den = np.sqrt(var_u * var_u.T)
        rho = np.where((n > 0) & (den > 1e-12), num / den, 0.0)
    return _finish(rho, n, shrinkage, min_support)
