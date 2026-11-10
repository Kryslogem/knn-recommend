"""Test metrics + quy tắc ứng viên. Dữ liệu nhỏ tự tạo chỉ để kiểm tra công thức."""

import math

import numpy as np
import pandas as pd
import pytest

from ml.eval.evaluate import evaluate_model, top_k_lists
from ml.eval.metrics import mae, ranking_metrics_for_user, rmse


def test_rmse_mae_handcalc():
    assert rmse([3, 4], [4, 2]) == pytest.approx(math.sqrt((1 + 4) / 2))
    assert mae([3, 4], [4, 2]) == pytest.approx(1.5)


def test_ranking_handcalc():
    p, r, n = ranking_metrics_for_user([1, 2, 3], {1, 3, 9}, k=3)
    assert p == pytest.approx(2 / 3) and r == pytest.approx(2 / 3)
    dcg = 1 / math.log2(2) + 1 / math.log2(4)
    idcg = 1 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
    assert n == pytest.approx(dcg / idcg)


def test_precision_divides_by_k_when_fewer_returned():
    p, r, n = ranking_metrics_for_user([5], {5}, k=10)
    assert p == pytest.approx(0.1) and r == 1.0 and n == pytest.approx(1.0)


def test_perfect_and_empty_cases():
    assert ranking_metrics_for_user([1, 2], {1, 2}, k=2)[2] == pytest.approx(1.0)
    assert ranking_metrics_for_user([7, 8], {1}, k=2) == (0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        ranking_metrics_for_user([1], set(), k=1)


def test_min_item_ratings_threshold_filters_candidates():
    from ml.eval.evaluate import allowed_mask, rank_from_scores

    catalog = np.arange(1, 7)
    counts = pd.Series({1: 100, 2: 3, 3: 50, 4: 49, 5: 0})  # phim 6 không có trong train
    assert allowed_mask(catalog, counts, 50).tolist() == [True, False, True, False, False, False]
    assert allowed_mask(catalog, counts, 0).all()
    est = np.array([[1.0, 9.0, 2.0, 8.0, 7.0, 6.0]])  # điểm cao nhất thuộc phim không đủ ngưỡng
    top = rank_from_scores(est, [1], catalog, {}, k=4, allowed=allowed_mask(catalog, counts, 50))
    assert top[1].tolist() == [3, 1]  # chỉ còn 2 ứng viên hợp lệ → trả ít hơn k, không chèn phim bị loại
    top = rank_from_scores(est, [1], catalog, {1: {3}}, k=4, allowed=allowed_mask(catalog, counts, 50))
    assert top[1].tolist() == [1]  # vẫn loại phim đã chấm


class _Stub:
    """Mô hình giả: điểm = movie_id / 100 (phim id lớn xếp trước) — chỉ để kiểm tra logic loại ứng viên."""

    def predict_frame(self, df):
        return pd.DataFrame({"est": 3.0, "source": "baseline", "n_neighbors": 0}, index=df.index)

    def score_matrix(self, users, catalog):
        row = np.asarray(catalog) / 100.0
        return np.tile(row, (len(users), 1)), np.zeros((len(users), len(catalog)), dtype=bool)


def test_candidates_exclude_train_and_extra_and_ties_by_id():
    catalog = np.arange(1, 21)
    train = pd.DataFrame({"user_id": 1, "movie_id": [20, 19], "rating": 5, "timestamp": 0})
    val = pd.DataFrame({"user_id": 1, "movie_id": [18], "rating": 5, "timestamp": 0})
    top = top_k_lists(_Stub(), [1], catalog, {1: {20, 19, 18}}, k=3)
    assert top[1].tolist() == [17, 16, 15]
    # hòa điểm → movie_id nhỏ trước
    class Tie(_Stub):
        def score_matrix(self, users, catalog):
            return np.ones((len(users), len(catalog))), np.zeros((len(users), len(catalog)), dtype=bool)

    assert top_k_lists(Tie(), [1], catalog, {}, k=3)[1].tolist() == [1, 2, 3]

    test = pd.DataFrame({"user_id": [1, 1], "movie_id": [17, 3], "rating": [5, 2], "timestamp": 0})
    m, preds = evaluate_model(_Stub(), test, train, catalog, extra_exclude=val, k=3)
    assert m["n_eligible_users"] == 1 and m["recall@3"] == 1.0  # 17 nằm đầu danh sách
    assert m["fallback_rate"] == 1.0 and len(preds) == 2
