"""Test API: xác thực, phân quyền, đầu vào, đánh giá, đề xuất, bền vững, admin."""

import pytest

from backend.app.config import Settings
from backend.app.main import create_app
from backend.tests.conftest import PASSWORD, make_user

API = "/api/v1"


# ---------- xác thực ----------
def test_register_login_me_and_duplicates(env):
    _, c, _ = env
    r = c.post(f"{API}/auth/register", json={"username": "Bob_1", "password": PASSWORD})
    assert r.status_code == 201 and r.json()["user"]["username"] == "bob_1" and r.json()["user"]["role"] == "user"
    assert c.post(f"{API}/auth/register", json={"username": "BOB_1", "password": PASSWORD}).status_code == 409
    tok = c.post(f"{API}/auth/login", json={"username": "bob_1", "password": PASSWORD}).json()["access_token"]
    me = c.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()
    assert me["username"] == "bob_1" and me["n_ratings"] == 0
    assert me["id"] > 30  # không trùng ID hồ sơ MovieLens (FR02)


def test_login_failures_and_missing_token(env, user_h):
    _, c, _ = env
    assert c.post(f"{API}/auth/login", json={"username": "alice", "password": "wrong-password-1"}).status_code == 401
    assert c.post(f"{API}/auth/login", json={"username": "nobody", "password": PASSWORD}).status_code == 401
    assert c.get(f"{API}/auth/me").status_code == 401
    assert c.get(f"{API}/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    # hồ sơ MovieLens không có mật khẩu → không đăng nhập được
    assert c.post(f"{API}/auth/login", json={"username": "ml1", "password": PASSWORD}).status_code == 401


@pytest.mark.parametrize("body", [
    {"username": "ab", "password": PASSWORD}, {"username": "bad name!", "password": PASSWORD},
    {"username": "okname", "password": "short"}, {"username": "okname"}, {},
])
def test_register_validation(env, body):
    _, c, _ = env
    r = c.post(f"{API}/auth/register", json=body)
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


def test_disabled_account_is_blocked(env, user_h, admin_h):
    _, c, _ = env
    uid = c.get(f"{API}/auth/me", headers=user_h).json()["id"]
    assert c.patch(f"{API}/admin/users/{uid}", json={"is_active": False}, headers=admin_h).status_code == 200
    assert c.get(f"{API}/auth/me", headers=user_h).status_code == 403
    assert c.post(f"{API}/auth/login", json={"username": "alice", "password": PASSWORD}).status_code == 403


def test_expired_token_rejected(env):
    app, c, _ = env
    from backend.app.security import create_token

    uid = make_user(app, "carol")
    tok = create_token(uid, app.state.settings.jwt_secret, -1)
    assert c.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


# ---------- phân quyền (NFR05) ----------
def test_role_enforcement(env, user_h, admin_h, ds_h):
    _, c, _ = env
    for path in ("/ds/models", "/ds/training-jobs", "/ds/data/report"):
        assert c.get(API + path, headers=user_h).status_code == 403
        assert c.get(API + path, headers=admin_h).status_code == 403  # admin không có quyền DS
        assert c.get(API + path).status_code == 401
    for path in ("/admin/status", "/admin/users"):
        assert c.get(API + path, headers=user_h).status_code == 403
        assert c.get(API + path, headers=ds_h).status_code == 403
    assert c.post(f"{API}/ds/training-jobs", json={}, headers=user_h).status_code == 403
    assert c.get(f"{API}/admin/status", headers=admin_h).status_code == 200
    assert c.get(f"{API}/ds/models", headers=ds_h).status_code == 200


def test_user_cannot_escalate_role_via_register(env):
    _, c, _ = env
    r = c.post(f"{API}/auth/register", json={"username": "evil", "password": PASSWORD, "role": "admin"})
    assert r.json()["user"]["role"] == "user"


# ---------- phim ----------
def test_movie_search_filter_pagination(env, user_h):
    _, c, _ = env
    r = c.get(f"{API}/movies", params={"q": "movie 0", "page_size": 5}, headers=user_h).json()
    assert r["total"] == 9 and len(r["items"]) == 5 and r["page_size"] == 5
    g = c.get(f"{API}/movies", params={"genre": "Comedy", "page_size": 100}, headers=user_h).json()
    assert g["total"] > 0 and all("Comedy" in m["genres"] for m in g["items"])
    y = c.get(f"{API}/movies", params={"year_from": 1995, "year_to": 1996, "page_size": 100}, headers=user_h).json()
    assert y["total"] > 0 and all(1995 <= m["year"] <= 1996 for m in y["items"])
    assert c.get(f"{API}/movies", params={"q": "%"}, headers=user_h).json()["total"] == 0  # % không phải ký tự đại diện
    for bad in ({"page_size": 101}, {"page": 0}, {"sort": "nope"}, {"q": "x" * 101}, {"year_from": "abc"}):
        assert c.get(f"{API}/movies", params=bad, headers=user_h).status_code == 422


def test_movie_detail_and_404(env, user_h):
    _, c, _ = env
    d = c.get(f"{API}/movies/1", headers=user_h).json()
    assert d["id"] == 1 and d["my_rating"] is None and d["n_ratings_train"] > 0
    assert c.get(f"{API}/movies/9999", headers=user_h).status_code == 404
    assert c.get(f"{API}/movies/abc", headers=user_h).status_code == 422


# ---------- đánh giá ----------
def test_rating_upsert_is_idempotent_and_persisted(env, user_h):
    app, c, tmp = env
    assert c.put(f"{API}/ratings/5", json={"rating": 4}, headers=user_h).json()["created"] is True
    r = c.put(f"{API}/ratings/5", json={"rating": 2}, headers=user_h).json()
    assert r["created"] is False and r["rating"] == 2
    assert c.put(f"{API}/ratings/5", json={"rating": 2}, headers=user_h).status_code == 200
    mine = c.get(f"{API}/ratings/me", headers=user_h).json()
    assert mine["total"] == 1 and mine["items"][0]["rating"] == 2  # đúng một điểm hiện hành
    assert c.get(f"{API}/movies/5", headers=user_h).json()["my_rating"] == 2
    # bền vững qua khởi động lại: dựng app mới trên cùng DB
    s2 = Settings(database_url=app.state.settings.database_url, artifacts_dir=app.state.settings.artifacts_dir,
                  jwt_secret=app.state.settings.jwt_secret)
    from fastapi.testclient import TestClient

    with TestClient(create_app(s2)) as c2:
        assert c2.get(f"{API}/ratings/me", headers=user_h).json()["items"][0]["rating"] == 2


@pytest.mark.parametrize("body", [{"rating": 0}, {"rating": 6}, {"rating": 3.5}, {"rating": "5"}, {"rating": None}, {}, {"rating": 3, "x": 1}, {"rating": True}])
def test_rating_rejects_bad_input(env, user_h, body):
    _, c, _ = env
    r = c.put(f"{API}/ratings/5", json=body, headers=user_h)
    assert r.status_code == 422, body
    assert c.get(f"{API}/ratings/me", headers=user_h).json()["total"] == 0  # không lưu gì


def test_rating_unknown_or_hidden_movie_and_delete(env, user_h, admin_h):
    _, c, _ = env
    assert c.put(f"{API}/ratings/9999", json={"rating": 3}, headers=user_h).status_code == 404
    assert c.patch(f"{API}/admin/movies/7", json={"is_hidden": True}, headers=admin_h).status_code == 200
    assert c.put(f"{API}/ratings/7", json={"rating": 3}, headers=user_h).status_code == 404
    assert c.get(f"{API}/movies/7", headers=user_h).status_code == 404
    c.put(f"{API}/ratings/8", json={"rating": 3}, headers=user_h)
    assert c.delete(f"{API}/ratings/8", headers=user_h).status_code == 200
    assert c.delete(f"{API}/ratings/8", headers=user_h).status_code == 404


def test_ratings_isolated_between_users(env, user_h):
    app, c, _ = env
    make_user(app, "dave")
    from backend.tests.conftest import login

    other = login(c, "dave")
    c.put(f"{API}/ratings/5", json={"rating": 5}, headers=user_h)
    assert c.get(f"{API}/ratings/me", headers=other).json()["total"] == 0


# ---------- đề xuất ----------
def test_new_user_gets_popular_then_personalised(env, user_h):
    _, c, _ = env
    r = c.get(f"{API}/recommendations", headers=user_h).json()
    assert r["profile_size"] == 0 and r["source_summary"]["popular"] == len(r["items"]) > 0 and r["message"]
    assert r["model_version"] == "v-test-1"
    for m in range(1, 9):
        c.put(f"{API}/ratings/{m}", json={"rating": 5 if m % 2 else 1}, headers=user_h)
    r = c.get(f"{API}/recommendations", params={"n": 10}, headers=user_h).json()
    assert r["profile_size"] == 8 and r["source_summary"]["popular"] == 0
    ids = [i["movie"]["id"] for i in r["items"]]
    assert not set(ids) & set(range(1, 9))  # không chứa phim đã chấm
    assert all(1 <= i["predicted_rating"] <= 5 and i["source"] in ("knn", "baseline") for i in r["items"])
    assert all(i["breakdown"] is not None for i in r["items"])


def test_editing_a_rating_changes_recommendations_and_busts_cache(env, user_h):
    _, c, _ = env
    for m in range(1, 13):
        c.put(f"{API}/ratings/{m}", json={"rating": 5}, headers=user_h)
    a = c.get(f"{API}/recommendations", params={"n": 20}, headers=user_h).json()
    assert c.get(f"{API}/recommendations", params={"n": 20}, headers=user_h).json()["cached"] is True
    for m in range(1, 13):
        c.put(f"{API}/ratings/{m}", json={"rating": 1}, headers=user_h)
    b = c.get(f"{API}/recommendations", params={"n": 20}, headers=user_h).json()
    assert b["cached"] is False and b["profile_size"] == 12
    assert [(i["movie"]["id"], i["predicted_rating"]) for i in a["items"]] != [(i["movie"]["id"], i["predicted_rating"]) for i in b["items"]]


def test_recommendation_filters_and_params(env, user_h, admin_h):
    _, c, _ = env
    for m in range(1, 9):
        c.put(f"{API}/ratings/{m}", json={"rating": 4}, headers=user_h)
    r = c.get(f"{API}/recommendations", params={"genre": "Drama", "n": 50}, headers=user_h).json()
    assert r["items"] and all("Drama" in i["movie"]["genres"] for i in r["items"])
    for bad in ({"n": 0}, {"n": 1000}, {"n": "x"}):
        assert c.get(f"{API}/recommendations", params=bad, headers=user_h).status_code == 422
    assert c.get(f"{API}/recommendations", params={"genre": "NoSuchGenre"}, headers=user_h).status_code == 422
    top = c.get(f"{API}/recommendations", params={"n": 5}, headers=user_h).json()["items"][0]["movie"]["id"]
    c.patch(f"{API}/admin/movies/{top}", json={"is_hidden": True}, headers=admin_h)  # ẩn → đổi đề xuất ngay
    after = c.get(f"{API}/recommendations", params={"n": 50}, headers=user_h).json()
    assert top not in [i["movie"]["id"] for i in after["items"]]


def test_explain_and_prediction(env, user_h):
    _, c, _ = env
    for m in range(1, 13):
        c.put(f"{API}/ratings/{m}", json={"rating": 4}, headers=user_h)
    e = c.get(f"{API}/recommendations/20/explain", headers=user_h).json()
    assert e["item"]["movie"]["id"] == 20 and e["item"]["breakdown"]["mu"] > 0
    assert c.get(f"{API}/movies/20/prediction", headers=user_h).json()["item"]["movie"]["id"] == 20
    # phim đã chấm vẫn dự đoán được (hồ sơ bỏ chính phim đó)
    assert c.get(f"{API}/movies/3/prediction", headers=user_h).json()["item"] is not None
    # phim không có trong train → không dự đoán, có thông báo
    unk = c.get(f"{API}/movies/50/prediction", headers=user_h).json()
    assert unk["item"] is None and unk["message"]
    assert c.get(f"{API}/recommendations/9999/explain", headers=user_h).status_code == 404


def test_popular_endpoint_excludes_rated(env, user_h):
    _, c, _ = env
    first = c.get(f"{API}/movies/popular", params={"n": 3}, headers=user_h).json()["items"]
    c.put(f"{API}/ratings/{first[0]['id']}", json={"rating": 3}, headers=user_h)
    again = c.get(f"{API}/movies/popular", params={"n": 3}, headers=user_h).json()["items"]
    assert first[0]["id"] not in [m["id"] for m in again]


def test_503_when_no_model(tmp_path):
    from fastapi.testclient import TestClient

    s = Settings(database_url=f"sqlite:///{(tmp_path / 'n.db').as_posix()}", artifacts_dir=str(tmp_path / "empty"),
                 jwt_secret="test-secret-not-for-production-use-0123456789")
    app = create_app(s)
    with TestClient(app) as c:
        make_user(app, "erin")
        from backend.tests.conftest import login

        h = login(c, "erin")
        r = c.get(f"{API}/recommendations", headers=h)
        assert r.status_code == 503 and r.json()["code"] == "model_not_loaded"
        assert c.get(f"{API}/health").json()["model_loaded"] is False


# ---------- admin ----------
def test_admin_status_users_and_guards(env, user_h, admin_h):
    _, c, _ = env
    c.put(f"{API}/ratings/5", json={"rating": 4}, headers=user_h)
    c.get(f"{API}/recommendations", headers=user_h)
    st = c.get(f"{API}/admin/status", headers=admin_h).json()
    assert st["model"]["version"] == "v-test-1" and st["movies"]["total"] == 50
    assert st["users"]["movielens"] == 30 and st["ratings"]["app"] == 1
    assert st["recommendations"]["requests"] >= 1 and st["recommendations"]["p50_ms"] is not None
    users = c.get(f"{API}/admin/users", params={"q": "ali"}, headers=admin_h).json()
    assert users["total"] == 1 and users["items"][0]["username"] == "alice"
    me = c.get(f"{API}/auth/me", headers=admin_h).json()["id"]
    assert c.patch(f"{API}/admin/users/{me}", json={"role": "user"}, headers=admin_h).status_code == 400
    assert c.patch(f"{API}/admin/users/1", json={"role": "admin"}, headers=admin_h).status_code == 404  # hồ sơ MovieLens
    assert c.patch(f"{API}/admin/users/{me + 1}", json={"role": "superuser"}, headers=admin_h).status_code == 422


def test_admin_movielens_recommendations_exclude_self(env, admin_h):
    _, c, _ = env
    r = c.get(f"{API}/admin/recommendations/movielens/3", params={"n": 5}, headers=admin_h).json()
    assert r["ml_user_id"] == 3 and r["profile_size"] > 0 and len(r["items"]) == 5
    assert c.get(f"{API}/admin/recommendations/movielens/9999", headers=admin_h).status_code == 404


# ---------- Data Scientist ----------
def test_models_listing_activation_and_hot_swap(env, ds_h, user_h):
    app, c, tmp = env
    from backend.tests.conftest import build_artifact

    build_artifact(tmp / "models", version="v-test-2", seed=9)  # như thể huấn luyện bằng CLI
    items = c.get(f"{API}/ds/models", headers=ds_h).json()["items"]
    assert {m["version"] for m in items} == {"v-test-1", "v-test-2"}
    assert [m["version"] for m in items if m["is_active"]] == ["v-test-1"]
    v2 = next(m for m in items if m["version"] == "v-test-2")
    assert c.get(f"{API}/recommendations", headers=user_h).json()["model_version"] == "v-test-1"
    assert c.post(f"{API}/ds/models/{v2['id']}/activate", headers=ds_h).status_code == 200
    assert c.get(f"{API}/recommendations", headers=user_h).json()["model_version"] == "v-test-2"  # không cần khởi động lại
    items = c.get(f"{API}/ds/models", headers=ds_h).json()["items"]
    assert [m["version"] for m in items if m["is_active"]] == ["v-test-2"]  # đúng một phiên bản active
    assert c.post(f"{API}/ds/models/9999/activate", headers=ds_h).status_code == 404


def test_activate_missing_artifact_keeps_current_model(env, ds_h, user_h):
    import shutil

    app, c, tmp = env
    from backend.tests.conftest import build_artifact

    build_artifact(tmp / "models", version="v-test-3", seed=5)
    mid = next(m["id"] for m in c.get(f"{API}/ds/models", headers=ds_h).json()["items"] if m["version"] == "v-test-3")
    shutil.rmtree(tmp / "models" / "v-test-3")
    r = c.post(f"{API}/ds/models/{mid}/activate", headers=ds_h)
    assert r.status_code == 409 and r.json()["code"] == "artifact_unavailable"
    assert c.get(f"{API}/recommendations", headers=user_h).json()["model_version"] == "v-test-1"


def test_reports_missing_returns_404_with_hint(env, ds_h):
    _, c, _ = env
    r = c.get(f"{API}/ds/data/report", headers=ds_h)
    assert r.status_code == 404 and r.json()["code"] == "report_missing"


def test_reports_served_when_present(env, ds_h):
    import json

    _, c, tmp = env
    rep = tmp / "reports"
    rep.mkdir()
    (rep / "comparison.json").write_text(json.dumps({"rows": [{"rmse": 0.9}]}), encoding="utf-8")
    (rep / "tuning.csv").write_text("k,val_rmse,val_ndcg@10\n10,0.93,\n20,0.92,0.1\n", encoding="utf-8")
    assert c.get(f"{API}/ds/evaluation/comparison", headers=ds_h).json()["rows"][0]["rmse"] == 0.9
    t = c.get(f"{API}/ds/evaluation/tuning", headers=ds_h).json()["items"]
    assert t[0]["val_ndcg@10"] is None and t[1]["k"] == 20.0


@pytest.mark.parametrize("body", [
    {"k": 0}, {"k": 1000}, {"shrinkage": -1}, {"reg_u": -5}, {"n_epochs": 0}, {"min_k": 0}, {"min_support": 0},
    {"min_item_ratings": -1}, {"k": "abc"}, {"unknown": 1},
])
def test_training_job_rejects_out_of_range(env, ds_h, body):
    _, c, _ = env
    assert c.post(f"{API}/ds/training-jobs", json=body, headers=ds_h).status_code == 422


def test_training_job_needs_prepared_data(env, ds_h):
    _, c, _ = env
    r = c.post(f"{API}/ds/training-jobs", json={}, headers=ds_h)
    assert r.status_code == 409 and r.json()["code"] == "data_not_prepared"


# ---------- job huấn luyện nền ----------
@pytest.fixture
def prepared(env):
    """Thư mục dữ liệu đã chia nhỏ (ngẫu nhiên, chỉ để chạy pipeline) cho job huấn luyện."""
    import json

    import numpy as np
    import pandas as pd

    app, c, tmp = env
    rng = np.random.default_rng(1)
    rows = [(u, i, int(rng.integers(1, 6))) for u in range(1, 31) for i in range(1, 47) if rng.random() < 0.45]
    df = pd.DataFrame(rows, columns=["user_id", "movie_id", "rating"])
    df["timestamp"] = 0
    val = df.sample(frac=0.2, random_state=0)
    d = tmp / "processed"
    d.mkdir()
    df.drop(val.index).to_csv(d / "train.csv", index=False)
    val.to_csv(d / "validation.csv", index=False)
    pd.DataFrame({"movie_id": range(1, 51)}).to_csv(d / "movies.csv", index=False)
    (d / "split_manifest.json").write_text(json.dumps({"u_data_sha256": "a" * 64, "split_hash": "b" * 64}), encoding="utf-8")
    return d


def test_training_job_succeeds_and_registers_version(env, ds_h, prepared):
    app, c, _ = env
    body = {"k": 5, "min_k": 2, "n_epochs": 3, "shrinkage": 10, "min_item_ratings": 2}
    jid = c.post(f"{API}/ds/training-jobs", json=body, headers=ds_h).json()["id"]
    app.state.trainer.wait(120)
    job = c.get(f"{API}/ds/training-jobs/{jid}", headers=ds_h).json()
    assert job["status"] == "succeeded", job["log"]
    assert job["config"]["knn"]["k"] == 5 and job["config"]["serving"]["min_item_ratings"] == 2
    assert "Hoàn tất" in job["log"] and job["model_version_id"]
    m = c.get(f"{API}/ds/models/{job['model_version_id']}", headers=ds_h).json()
    assert m["is_active"] is False and m["metrics_test"] is None  # job web không gắn metrics test
    assert m["metrics_val"]["rmse"] > 0 and m["includes_app_ratings"] is False
    assert c.get(f"{API}/ds/training-jobs", headers=ds_h).json()["items"][0]["id"] == jid


def test_training_job_failure_is_recorded_and_blocks_while_running(env, ds_h, prepared):
    app, c, _ = env
    from backend.app.models import TrainingJob

    with app.state.SessionLocal() as db:  # giả lập job đang chạy
        db.add(TrainingJob(status="running", config={}))
        db.commit()
    r = c.post(f"{API}/ds/training-jobs", json={}, headers=ds_h)
    assert r.status_code == 409 and r.json()["code"] == "job_running"
    with app.state.SessionLocal() as db:
        for j in db.query(TrainingJob):
            j.status = "failed"
        db.commit()
    (prepared / "train.csv").write_text("user_id,movie_id\n1,1\n", encoding="utf-8")  # thiếu cột rating
    jid = c.post(f"{API}/ds/training-jobs", json={}, headers=ds_h).json()["id"]
    app.state.trainer.wait(60)
    job = c.get(f"{API}/ds/training-jobs/{jid}", headers=ds_h).json()
    assert job["status"] == "failed" and "LỖI" in job["log"] and job["finished_at"]
    assert c.get(f"{API}/ds/training-jobs/9999", headers=ds_h).status_code == 404


def test_admin_movie_listing_includes_hidden(env, admin_h, user_h):
    _, c, _ = env
    c.patch(f"{API}/admin/movies/7", json={"is_hidden": True}, headers=admin_h)
    allm = c.get(f"{API}/admin/movies", params={"page_size": 100}, headers=admin_h).json()
    assert allm["total"] == 50 and any(m["id"] == 7 and m["is_hidden"] for m in allm["items"])
    only = c.get(f"{API}/admin/movies", params={"hidden": "true"}, headers=admin_h).json()
    assert [m["id"] for m in only["items"]] == [7]
    assert c.get(f"{API}/admin/movies", headers=user_h).status_code == 403
    assert c.get(f"{API}/admin/movies", params={"page_size": 500}, headers=admin_h).status_code == 422
