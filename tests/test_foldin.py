"""Test fold-in, đề xuất và artifact. Dữ liệu ngẫu nhiên nhỏ chỉ để kiểm tra logic, không dùng đánh giá ML."""

import numpy as np
import pandas as pd
import pytest

from ml.models.artifact import load_artifact, save_artifact
from ml.models.foldin import fold_in, recommend
from ml.models.knn import KNNModel
from ml.models.popular import PopularModel
from ml.models.similarity import profile_similarity_baseline, profile_similarity_pearson


@pytest.fixture(scope="module")
def train():
    rng = np.random.default_rng(11)
    rows = [(u, i, int(rng.integers(1, 6))) for u in range(1, 41) for i in range(1, 61) if rng.random() < 0.4]
    return pd.DataFrame(rows, columns=["user_id", "movie_id", "rating"])


@pytest.fixture(scope="module", params=["baseline", "basic"])
def model(request, train):
    return KNNModel(request.param, k=8, min_k=2, shrinkage=20, min_support=2, n_epochs=8, reg_u=10, reg_i=8).fit(train)


@pytest.fixture(scope="module")
def popular(train):
    return PopularModel(5).fit(train)


def _history(train, uid):
    g = train[train.user_id == uid]
    return dict(zip(g.movie_id, g.rating))


def test_profile_similarity_equals_matrix_row(model):
    rm = model.rm
    for u in (0, 7, 25):
        if model.mode == "baseline":
            row = profile_similarity_baseline(model.V, rm.M, model.V[u], rm.M[u], model.shrinkage, model.min_support)
        else:
            row = profile_similarity_pearson(rm.R, rm.M, rm.R[u], rm.M[u], model.shrinkage, model.min_support)
        expected = model.sim[u].copy()
        row = row.copy()
        row[u] = 0.0  # hồ sơ trùng user u sẽ tương đồng với chính hàng của u
        np.testing.assert_allclose(row, expected, atol=1e-10)


def test_foldin_exactly_reproduces_fitted_predictions(model, popular):
    """Với bias hồ sơ = bias đã học và loại chính user đó: kết quả phải TRÙNG KHỚP predict của mô hình đã fit."""
    uid = 5
    uidx = model.rm.user_index[uid]
    override = model.bias.b_u[uidx] if model.mode == "baseline" else None
    res = recommend(model, popular, _history(model_train(model), uid), n=1000, exclude_user_id=uid,
                    bias_override=override, with_neighbors=False)
    got = {it["movie_id"]: it for it in res["items"]}
    assert got, "phải có ứng viên"
    items = np.array([model.rm.item_index[m] for m in got])
    est, use_knn, nn = model._predict_user_items(uidx, items)
    for m, e, k_, n_ in zip(got, est, use_knn, nn):
        assert got[m]["predicted_rating"] == pytest.approx(e, abs=1e-4)
        assert got[m]["source"] == ("knn" if k_ else "baseline") and got[m]["n_neighbors"] == n_


def model_train(model):
    rm = model.rm
    rows = [(rm.user_ids[u], rm.item_ids[i], int(rm.R[u, i])) for u, i in zip(*np.nonzero(rm.M))]
    return pd.DataFrame(rows, columns=["user_id", "movie_id", "rating"])


def test_estimated_bias_equals_learned_bias_for_same_history(train):
    """Vòng ALS cuối cập nhật b_u bằng đúng công thức một bước với b_i cuối → fold-in cùng lịch sử cho đúng b_u."""
    m = KNNModel("baseline", k=8, min_k=2, shrinkage=20, n_epochs=10, reg_u=10, reg_i=8).fit(train)
    for u in range(1, 41):
        assert fold_in(m, _history(train, u)).b_q == pytest.approx(m.bias.b_u[m.rm.user_index[u]], abs=1e-12)


def test_rated_items_never_recommended_and_deterministic(model, popular, train):
    hist = _history(train, 3)
    a = recommend(model, popular, hist, n=15)
    b = recommend(model, popular, hist, n=15)
    assert a == b
    assert not {it["movie_id"] for it in a["items"]} & set(hist)
    assert all(1.0 <= it["predicted_rating"] <= 5.0 for it in a["items"])


def test_filters_and_thresholds(model, popular, train):
    hist = _history(train, 3)
    counts = model.rm.M.sum(axis=0)
    res = recommend(model, popular, hist, n=50, min_item_ratings=int(np.median(counts)))
    ids = [it["movie_id"] for it in res["items"]]
    assert all(counts[model.rm.item_index[m]] >= np.median(counts) for m in ids)
    allowed = set(ids[:4])
    res2 = recommend(model, popular, hist, n=50, allowed_ids=allowed)
    assert {it["movie_id"] for it in res2["items"]} <= allowed
    res3 = recommend(model, popular, hist, n=10, exclude_ids=allowed)
    assert not {it["movie_id"] for it in res3["items"]} & allowed
    tiny = recommend(model, popular, hist, n=50, allowed_ids=list(allowed))
    assert tiny["message"] and "Chỉ có" in tiny["message"]


def test_cold_start_returns_popular(model, popular):
    res = recommend(model, popular, {}, n=5)
    assert res["profile_size"] == 0 and res["source_summary"] == {"knn": 0, "baseline": 0, "popular": 5}
    assert res["message"]
    scores = [it["predicted_rating"] for it in res["items"]]
    assert scores == sorted(scores, reverse=True)
    # hồ sơ chỉ gồm phim mô hình không biết → cũng là cold start, báo phim bị bỏ
    res = recommend(model, popular, {99999: 5}, n=5)
    assert res["source_summary"]["popular"] == 5 and res["dropped_unknown_items"] == [99999]


def test_popular_cold_start_respects_rated_and_filters(model, popular):
    first = recommend(model, popular, {}, n=3)["items"]
    banned = {first[0]["movie_id"]}
    res = recommend(model, popular, {}, n=3, exclude_ids=banned)
    assert not {it["movie_id"] for it in res["items"]} & banned


def test_changing_a_rating_changes_recommendations(model, popular, train):
    hist = _history(train, 4)
    top = max(hist, key=lambda m: hist[m])
    before = recommend(model, popular, hist, n=30)
    flipped = {**hist, top: 1 if hist[top] >= 4 else 5}
    after = recommend(model, popular, flipped, n=30)
    assert before["items"] != after["items"]


@pytest.mark.parametrize("bad", [0, 6, 3.5, "5", None, True])
def test_invalid_ratings_rejected(model, popular, bad):
    with pytest.raises(ValueError):
        recommend(model, popular, {1: bad})


def test_neighbors_explanation_fields(train):
    m = KNNModel("baseline", k=8, min_k=2, shrinkage=20, n_epochs=8).fit(train)
    p = PopularModel(5).fit(train)
    res = recommend(m, p, _history(train, 2), n=5)
    knn_items = [it for it in res["items"] if it["source"] == "knn"]
    assert knn_items
    for it in knn_items:
        assert 1 <= len(it["neighbors"]) <= 3
        assert all(n["similarity"] > 0 and 1 <= n["rating"] <= 5 for n in it["neighbors"])
        b = it["breakdown"]
        if not b["clipped"]:
            assert it["predicted_rating"] == pytest.approx(b["mu"] + b["b_user"] + b["b_item"] + b["neighbor_term"], abs=1e-3)


def test_artifact_roundtrip_is_exact(tmp_path, model, popular, train):
    meta = {
        "version": "t-1",
        "params": {"mode": model.mode, "k": model.k, "min_k": model.min_k, "shrinkage": model.shrinkage,
                   "min_support": model.min_support, "n_epochs": model.n_epochs, "reg_u": model.reg_u, "reg_i": model.reg_i},
        "serving": {"min_item_ratings": 0, "popular_bayes_m": 5},
    }
    path = save_artifact(tmp_path / "t-1", model, popular, meta, {"validation": {}})
    with pytest.raises(FileExistsError):
        save_artifact(path, model, popular, meta, {})  # phiên bản bất biến
    b = load_artifact(path)
    np.testing.assert_array_equal(b.knn.sim, model.sim)
    np.testing.assert_array_equal(b.knn.V, model.V)
    hist = _history(train, 6)
    assert recommend(b.knn, b.popular, hist, n=20) == recommend(model, popular, hist, n=20)
    assert recommend(b.knn, b.popular, {}, n=5) == recommend(model, popular, {}, n=5)
