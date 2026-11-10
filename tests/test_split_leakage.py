"""Test chia dữ liệu: rời nhau, đủ, tái lập, không rò rỉ. Dùng dữ liệu nhỏ chỉ để kiểm tra công thức."""

import pandas as pd
import pytest

from ml.data.split import split_per_user, split_sizes
from ml.data.validate import clean_ratings, validate


def _toy(n_users=30, n_items=60):
    rows = [(u, i, 1 + (u * 7 + i * 3) % 5, 1000 + u + i) for u in range(1, n_users + 1) for i in range(1, n_items + 1) if (u + i) % 2 == 0]
    return pd.DataFrame(rows, columns=["user_id", "movie_id", "rating", "timestamp"])


def _pairs(df):
    return set(zip(df["user_id"], df["movie_id"]))


def test_splits_are_disjoint_and_complete():
    df = _toy()
    s = split_per_user(df, seed=1, val_frac=0.15, test_frac=0.15)
    tr, va, te = (_pairs(s[k]) for k in ("train", "validation", "test"))
    assert not (tr & va) and not (tr & te) and not (va & te)
    assert tr | va | te == _pairs(df)
    assert sum(len(v) for v in s.values()) == len(df)


def test_every_user_in_train_and_sizes_match_rule():
    df = _toy()
    s = split_per_user(df, seed=1, val_frac=0.15, test_frac=0.15)
    assert set(s["train"]["user_id"]) == set(df["user_id"])
    for u, n in df.groupby("user_id").size().items():
        n_tr, n_va, n_te = split_sizes(n, 0.15, 0.15)
        assert (s["train"].user_id == u).sum() == n_tr
        assert (s["validation"].user_id == u).sum() == n_va
        assert (s["test"].user_id == u).sum() == n_te


def test_reproducible_and_input_order_independent():
    df = _toy()
    a = split_per_user(df, 7, 0.15, 0.15)
    b = split_per_user(df.sample(frac=1, random_state=0), 7, 0.15, 0.15)
    for k in a:
        pd.testing.assert_frame_equal(a[k], b[k])
    c = split_per_user(df, 8, 0.15, 0.15)
    assert not a["test"].equals(c["test"])


def test_split_sizes_rejects_empty_train():
    with pytest.raises(ValueError):
        split_sizes(1, 0.5, 0.5)


def test_clean_ratings_keeps_latest_duplicate():
    df = pd.DataFrame({"user_id": [1, 1], "movie_id": [5, 5], "rating": [2, 4], "timestamp": [10, 20]})
    out, dropped = clean_ratings(df)
    assert dropped == 1 and out.loc[0, "rating"] == 4


def test_validate_flags_out_of_range_rating():
    ratings = pd.DataFrame({"user_id": [1], "movie_id": [1], "rating": [9], "timestamp": [1]})
    items = pd.DataFrame({"movie_id": [1], "title": ["A (1990)"], "genres": [["Drama"]], "year": [1990]})
    exp = {"rating_min": 1, "rating_max": 5, "n_users": 1, "n_items": 1, "n_ratings": 1}
    assert validate(ratings, items, exp)["ok"] is False
