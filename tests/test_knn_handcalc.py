"""Test dự đoán KNN: tính tay + đối chiếu bản vòng lặp ngây thơ."""

import numpy as np
import pandas as pd
import pytest

from ml.models.baseline import fit_als
from ml.models.knn import KNNModel, neighbor_aggregate
from ml.models.matrix import RatingMatrix
from ml.models.popular import PopularModel
from ml.models.similarity import pearson_baseline

# user 0 là truy vấn; phim 0 do user 1,2,3 chấm với residual 1, 2, 9
SIM = np.array([0.0, 0.5, 0.25, -0.3])
V = np.array([[0, 0], [1.0, 0], [2.0, 0], [9.0, 0]])
M = np.array([[0, 0], [1, 0], [1, 0], [1, 0]], dtype=bool)
ITEMS = np.array([0, 1])


def test_aggregate_handcalc_k2_ignores_negative_similarity():
    agg, nn, _ = neighbor_aggregate(SIM, V, M, ITEMS, k=2)
    assert nn.tolist() == [2, 0]  # user 3 (s<0) bị loại; phim 1 không ai chấm
    assert agg[0] == pytest.approx((0.5 * 1 + 0.25 * 2) / 0.75)
    assert agg[1] == 0.0


def test_aggregate_top_k_picks_most_similar():
    agg, nn, _ = neighbor_aggregate(SIM, V, M, ITEMS, k=1)
    assert nn[0] == 1 and agg[0] == pytest.approx(1.0)


def _train(seed=5, n_u=25, n_i=40, p=0.35):
    rng = np.random.default_rng(seed)
    rows = [(u, i, int(rng.integers(1, 6))) for u in range(1, n_u + 1) for i in range(1, n_i + 1) if rng.random() < p]
    return pd.DataFrame(rows, columns=["user_id", "movie_id", "rating"])


def _naive_predict(model, uid, iid):
    rm = model.rm
    u, i = rm.user_index[uid], rm.item_index[iid]
    cands = [(model.sim[u, v], v) for v in range(rm.shape[0]) if rm.M[v, i] and model.sim[u, v] > 0]
    cands = sorted(cands, key=lambda t: -t[0])[: model.k]
    base = model.base[u, i]
    if len(cands) < model.min_k:
        return float(np.clip(base if model.mode == "baseline" else model.mu, 1, 5)), "baseline"
    w = sum(s for s, _ in cands)
    agg = sum(s * model.V[v, i] for s, v in cands) / w
    return float(np.clip(base + agg if model.mode == "baseline" else agg, 1, 5)), "knn"


@pytest.mark.parametrize("mode", ["baseline", "basic"])
@pytest.mark.parametrize("min_k", [1, 3])
def test_predict_matches_naive_and_is_clipped(mode, min_k):
    train = _train()
    model = KNNModel(mode=mode, k=5, min_k=min_k, shrinkage=10, n_epochs=5).fit(train)
    targets = train.sample(60, random_state=1)  # pairs đã quan sát (vẫn hợp lệ để so công thức)
    out = model.predict_frame(targets)
    for (idx, row), (_, r) in zip(out.iterrows(), targets.iterrows()):
        est, src = _naive_predict(model, int(r.user_id), int(r.movie_id))
        assert row["est"] == pytest.approx(est) and row["source"] == src
        assert 1.0 <= row["est"] <= 5.0


def test_min_k_triggers_baseline_fallback_and_unknown_ids():
    train = _train()
    model = KNNModel(mode="baseline", k=5, min_k=10_000, shrinkage=10).fit(train)
    out = model.predict_frame(pd.DataFrame({"user_id": [1, 1, 999], "movie_id": [2, 9999, 2]}))
    assert (out["source"] == "baseline").all()
    assert (out["n_neighbors"] < 10_000).all()  # ghi số láng giềng thực tế, dưới min_k
    assert out["n_neighbors"].iloc[1:].eq(0).all()  # phim lạ / user lạ → 0
    bias = fit_als(RatingMatrix.from_frame(train), 10, 15, 10)
    rm = RatingMatrix.from_frame(train)
    assert out["est"].iloc[0] == pytest.approx(np.clip(bias.full()[rm.user_index[1], rm.item_index[2]], 1, 5))
    # phim lạ: mu + b_u ; user lạ: mu + b_i
    assert out["est"].iloc[1] == pytest.approx(np.clip(bias.mu + bias.b_u[rm.user_index[1]], 1, 5))
    assert out["est"].iloc[2] == pytest.approx(np.clip(bias.mu + bias.b_i[rm.item_index[2]], 1, 5))


def test_invalid_hyperparameters():
    with pytest.raises(ValueError):
        KNNModel(k=0)
    with pytest.raises(ValueError):
        KNNModel(mode="nope")


def test_popular_bayes_handcalc_and_top_n():
    train = pd.DataFrame({"user_id": [1, 2, 3, 1], "movie_id": [1, 1, 1, 2], "rating": [5, 5, 5, 1]})
    p = PopularModel(m=2).fit(train)  # mu = 4
    assert p.score[1] == pytest.approx((15 + 2 * 4) / 5)
    assert p.score[2] == pytest.approx((1 + 2 * 4) / 3)
    assert [m for m, _ in p.top_n(5)] == [1, 2]
    assert [m for m, _ in p.top_n(5, exclude={1})] == [2]
    assert p.predict(1, 12345) == pytest.approx(4.0)  # phim lạ → mu


def test_similarity_is_built_from_train_only_signature():
    # fit() chỉ nhận train; ma trận similarity có kích thước theo số user train
    train = _train()
    model = KNNModel(k=5).fit(train)
    assert model.sim.shape == (train["user_id"].nunique(),) * 2
    assert pearson_baseline(model.V, model.rm.M, 100, 1).shape == model.sim.shape
