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


def _finish(rho: np.ndarray, n_common: np.ndarray, shrinkage: float, min_support: int) -> np.ndarray:
    denom = n_common - 1 + shrinkage
    with np.errstate(divide="ignore", invalid="ignore"):
        factor = np.where(denom > 0, (n_common - 1) / denom, 0.0)
    sim = rho * factor
    sim[n_common < max(min_support, 2)] = 0.0
    sim = np.clip(sim, -1.0, 1.0)  # chặn sai số làm tròn
    np.fill_diagonal(sim, 0.0)
    return sim


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
