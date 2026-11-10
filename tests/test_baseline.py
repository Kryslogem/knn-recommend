"""Test ALS bias. Dữ liệu nhỏ tự tạo CHỈ để kiểm tra công thức, không dùng đánh giá ML."""

import numpy as np
import pandas as pd
import pytest

from ml.models.baseline import BiasOnlyModel, fit_als
from ml.models.matrix import RatingMatrix

# 2 user × 2 item, tính tay: mu = 3.5
TOY = pd.DataFrame(
    {"user_id": [1, 1, 2, 2], "movie_id": [1, 2, 1, 2], "rating": [5, 3, 4, 2]}
)


def test_als_handcalc_no_reg():
    rm = RatingMatrix.from_frame(TOY)
    p = fit_als(rm, n_epochs=1, reg_u=0, reg_i=0)
    assert p.mu == pytest.approx(3.5)
    np.testing.assert_allclose(p.b_i, [1.0, -1.0])  # ((1.5)+(0.5))/2 ; ((-0.5)+(-1.5))/2
    np.testing.assert_allclose(p.b_u, [0.5, -0.5])
    # ma trận cộng tính hoàn hảo → tái tạo đúng rating
    np.testing.assert_allclose(p.full(), [[5, 3], [4, 2]])


def test_als_handcalc_with_item_reg():
    rm = RatingMatrix.from_frame(TOY)
    p = fit_als(rm, n_epochs=1, reg_u=0, reg_i=1)
    # b_i = sum(r - mu) / (reg_i + n_i) = 2/3 và -2/3
    np.testing.assert_allclose(p.b_i, [2 / 3, -2 / 3])


def test_objective_never_increases():
    rng = np.random.default_rng(0)
    rows = [(u, i, int(rng.integers(1, 6))) for u in range(1, 21) for i in range(1, 31) if rng.random() < 0.4]
    rm = RatingMatrix.from_frame(pd.DataFrame(rows, columns=["user_id", "movie_id", "rating"]))
    h = fit_als(rm, n_epochs=15, reg_u=5, reg_i=5).objective_history
    assert all(b <= a + 1e-9 for a, b in zip(h, h[1:]))


def test_bias_only_unknown_ids_use_zero_bias_and_clip():
    m = BiasOnlyModel(n_epochs=1, reg_u=0, reg_i=0).fit(TOY)
    assert m.predict(1, 1) == pytest.approx(5.0)
    assert m.predict(99, 99) == pytest.approx(3.5)  # mu + 0 + 0
    assert m.predict(99, 1) == pytest.approx(4.5)  # mu + 0 + b_i


def test_negative_hyperparameters_rejected():
    with pytest.raises(ValueError):
        fit_als(RatingMatrix.from_frame(TOY), reg_u=-1)
