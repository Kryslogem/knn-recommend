"""Test similarity: tính tay + đối chiếu bản vòng lặp ngây thơ trên ma trận thưa ngẫu nhiên."""

import numpy as np
import pytest

from ml.models.similarity import pearson, pearson_baseline


def _toy():
    # u0 chấm phim 0,1,2 ; u1 chấm phim 0,1,3 ; chung = {0,1}
    E = np.array([[1.0, -1.0, 2.0, 0.0], [2.0, -1.0, 0.0, 5.0]])
    M = np.array([[1, 1, 1, 0], [1, 1, 0, 1]], dtype=bool)
    return E, M


def test_pearson_baseline_handcalc():
    E, M = _toy()
    # num = 1*2 + (-1)(-1) = 3 ; sq_u0 = 1+1 = 2 ; sq_u1 = 4+1 = 5 ; rho = 3/sqrt(10)
    rho = 3 / np.sqrt(10)
    assert pearson_baseline(E, M, shrinkage=0)[0, 1] == pytest.approx(rho)
    # |I_uv| = 2 → shrink = 1/(1+2)
    assert pearson_baseline(E, M, shrinkage=2)[0, 1] == pytest.approx(rho / 3)
    # min_support = 3 > 2 phim chung → 0
    assert pearson_baseline(E, M, shrinkage=0, min_support=3)[0, 1] == 0.0


def test_no_common_items_and_diagonal_zero():
    E = np.array([[1.0, 0.0], [0.0, 2.0]])
    M = np.array([[1, 0], [0, 1]], dtype=bool)
    s = pearson_baseline(E, M, shrinkage=0)
    assert s[0, 1] == 0.0 and s[0, 0] == 0.0 and s[1, 1] == 0.0


def _naive(R, M, resid: bool, shrinkage, min_support):
    n = R.shape[0]
    S = np.zeros((n, n))
    for u in range(n):
        for v in range(n):
            if u == v:
                continue
            I = np.flatnonzero(M[u] & M[v])
            if len(I) < max(min_support, 2):
                continue
            a, b = R[u, I], R[v, I]
            if not resid:
                a, b = a - a.mean(), b - b.mean()
            den = np.sqrt((a**2).sum() * (b**2).sum())
            if den < 1e-12:
                continue
            rho = (a * b).sum() / den
            denom = len(I) - 1 + shrinkage
            S[u, v] = rho * ((len(I) - 1) / denom if denom > 0 else 0.0)
    return S


@pytest.mark.parametrize("shrinkage,min_support", [(0, 1), (25, 3)])
def test_vectorised_matches_naive(shrinkage, min_support):
    rng = np.random.default_rng(3)
    M = rng.random((15, 25)) < 0.4
    R = np.where(M, rng.integers(1, 6, (15, 25)).astype(float), 0.0)
    E = np.where(M, R - 3.5 + rng.normal(0, 0.3, R.shape), 0.0)

    sb = pearson_baseline(E, M, shrinkage, min_support)
    np.testing.assert_allclose(sb, _naive(E, M, True, shrinkage, min_support), atol=1e-9)
    sp = pearson(R, M, shrinkage, min_support)
    np.testing.assert_allclose(sp, _naive(R, M, False, shrinkage, min_support), atol=1e-9)
    for s in (sb, sp):
        np.testing.assert_allclose(s, s.T, atol=1e-12)  # đối xứng
        assert s.min() >= -1 and s.max() <= 1
