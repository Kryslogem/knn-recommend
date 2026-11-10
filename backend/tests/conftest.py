"""Fixture API: app độc lập + SQLite tạm + một artifact nhỏ.

Dữ liệu ở đây là ngẫu nhiên và CHỈ để kiểm tra logic API; không dùng cho đánh giá ML.
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.models import Genre, Movie, Rating, User
from backend.app.security import hash_password
from ml.models.artifact import save_artifact
from ml.models.knn import KNNModel
from ml.models.popular import PopularModel

N_USERS, N_MOVIES = 30, 50
GENRES = ["Action", "Comedy", "Drama"]
PASSWORD = "test-password-123"  # chỉ cho test cục bộ


def build_artifact(models_dir, version="v-test-1", seed=3):
    rng = np.random.default_rng(seed)
    rows = [(u, i, int(rng.integers(1, 6))) for u in range(1, N_USERS + 1) for i in range(1, N_MOVIES - 4) if rng.random() < 0.45]
    train = pd.DataFrame(rows, columns=["user_id", "movie_id", "rating"])  # phim 47–50 không có trong train
    knn = KNNModel("baseline", k=8, min_k=2, shrinkage=20, min_support=2, n_epochs=6, reg_u=10, reg_i=8).fit(train)
    pop = PopularModel(5).fit(train)
    meta = {
        "version": version, "algorithm": "knn_baseline",
        "params": {"mode": "baseline", "k": 8, "min_k": 2, "shrinkage": 20, "min_support": 2, "n_epochs": 6, "reg_u": 10, "reg_i": 8},
        "serving": {"min_item_ratings": 3, "popular_bayes_m": 5},
        "data_hash": "d" * 64, "split_hash": "s" * 64, "includes_app_ratings": False,
        "created_at": datetime.now().isoformat(),
    }
    save_artifact(models_dir / version, knn, pop, meta, {"validation": {"rmse": 1.0}, "test": None})
    return train


@pytest.fixture
def env(tmp_path):
    models = tmp_path / "models"
    train = build_artifact(models)
    (models / "active.json").write_text(json.dumps({"version": "v-test-1"}), encoding="utf-8")
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        artifacts_dir=str(models), reports_dir=str(tmp_path / "reports"), processed_dir=str(tmp_path / "processed"),
        jwt_secret="test-secret-not-for-production-use-0123456789", cors_origins=["http://localhost:5173"],
    )
    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.SessionLocal() as db:
            genres = {n: Genre(name=n) for n in GENRES}
            db.add_all(genres.values())
            for i in range(1, N_MOVIES + 1):
                db.add(Movie(id=i, title=f"Movie {i:02d} ({1990 + i % 10})", year=1990 + i % 10, genres=[genres[GENRES[i % 3]]]))
            for u in range(1, N_USERS + 1):  # hồ sơ MovieLens: id = ml_user_id
                db.add(User(id=u, kind="movielens", ml_user_id=u, role="user", is_active=False))
            db.flush()
            db.execute(Rating.__table__.insert(), [
                {"user_id": int(r.user_id), "movie_id": int(r.movie_id), "rating": int(r.rating), "source": "movielens"}
                for r in train.itertuples()
            ])
            db.commit()
        yield app, client, tmp_path


def make_user(app, username, role="user"):
    with app.state.SessionLocal() as db:
        u = User(username=username, password_hash=hash_password(PASSWORD), role=role, kind="app")
        db.add(u)
        db.commit()
        return u.id


def login(client, username):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def user_h(env):
    app, client, _ = env
    make_user(app, "alice")
    return login(client, "alice")


@pytest.fixture
def admin_h(env):
    app, client, _ = env
    make_user(app, "root", "admin")
    return login(client, "root")


@pytest.fixture
def ds_h(env):
    app, client, _ = env
    make_user(app, "scientist", "data_scientist")
    return login(client, "scientist")
