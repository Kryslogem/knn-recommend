"""Đề xuất: gọi fold-in thật trong tiến trình, cache theo (user, phiên bản, bộ lọc), đo độ trễ."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.errors import AppError
from backend.app.models import Genre, Movie, Rating, movie_genres
from backend.app.registry import ModelRegistry
from ml.models.foldin import recommend

CACHE_MAX = 2000


class RecommendService:
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self._cache: OrderedDict[tuple, dict] = OrderedDict()
        self._lock = threading.Lock()
        self.samples: deque[dict] = deque(maxlen=500)  # vòng đệm cho /admin/status

    # ---- cache ----
    def invalidate_user(self, user_id: int) -> None:
        with self._lock:
            for key in [k for k in self._cache if k[0] == user_id]:
                del self._cache[key]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    # ---- thống kê ----
    def latency_summary(self) -> dict:
        s = list(self.samples)
        if not s:
            return {"requests": 0, "p50_ms": None, "p95_ms": None, "fallback_rate": None}
        ms = np.array([x["ms"] for x in s])
        items = sum(x["items"] for x in s)
        return {
            "requests": len(s),
            "p50_ms": round(float(np.percentile(ms, 50)), 2),
            "p95_ms": round(float(np.percentile(ms, 95)), 2),
            "fallback_rate": round(sum(x["fallback"] for x in s) / items, 4) if items else None,
        }

    # ---- tính đề xuất ----
    def _bundle(self):
        b = self.registry.get()
        if b is None:
            raise AppError(503, "model_not_loaded", "Chưa có mô hình nào được kích hoạt. Data Scientist cần huấn luyện và kích hoạt một phiên bản.")
        return b

    @staticmethod
    def user_ratings(db: Session, user_id: int) -> dict[int, int]:
        return {m: r for m, r in db.execute(select(Rating.movie_id, Rating.rating).where(Rating.user_id == user_id))}

    @staticmethod
    def _filters(db: Session, genre: str | None) -> tuple[set[int], set[int] | None]:
        hidden = set(db.scalars(select(Movie.id).where(Movie.is_hidden.is_(True))))
        allowed = None
        if genre is not None:
            allowed = set(
                db.scalars(
                    select(movie_genres.c.movie_id).join(Genre, Genre.id == movie_genres.c.genre_id).where(Genre.name == genre)
                )
            )
        return hidden, allowed

    def recommend_for(
        self, db: Session, user_id: int, n: int, genre: str | None = None,
        exclude_user_id: int | None = None, use_cache: bool = True,
    ) -> dict:
        bundle = self._bundle()
        key = (user_id, bundle.version, n, genre)
        if use_cache:
            with self._lock:
                hit = self._cache.get(key)
                if hit is not None:
                    self._cache.move_to_end(key)
            if hit is not None:
                return {**hit, "cached": True}
        ratings = self.user_ratings(db, user_id)
        hidden, allowed = self._filters(db, genre)
        t0 = time.perf_counter()
        res = recommend(
            bundle.knn, bundle.popular, ratings, n=n, min_item_ratings=bundle.min_item_ratings,
            exclude_ids=hidden, allowed_ids=allowed, exclude_user_id=exclude_user_id,
        )
        ms = (time.perf_counter() - t0) * 1000
        out = self._finish(db, res, bundle, ms)
        self.samples.append({"ms": ms, "items": len(res["items"]), "fallback": sum(1 for i in res["items"] if i["source"] != "knn")})
        if use_cache:
            with self._lock:
                self._cache[key] = out
                while len(self._cache) > CACHE_MAX:
                    self._cache.popitem(last=False)
        return {**out, "cached": False}

    def predict_one(self, db: Session, user_id: int, movie_id: int) -> dict:
        """Điểm dự đoán + giải thích cho MỘT phim, dựng hồ sơ từ các điểm khác (bỏ chính phim này)."""
        bundle = self._bundle()
        ratings = {m: r for m, r in self.user_ratings(db, user_id).items() if m != movie_id}
        t0 = time.perf_counter()
        res = recommend(bundle.knn, bundle.popular, ratings, n=1, min_item_ratings=0, allowed_ids={movie_id})
        out = self._finish(db, res, bundle, (time.perf_counter() - t0) * 1000)
        out["item"] = out["items"][0] if out["items"] else None
        if out["item"] is None:
            out["message"] = "Mô hình hiện tại chưa biết phim này (không có trong dữ liệu huấn luyện)."
        del out["items"]
        return {**out, "cached": False}

    @staticmethod
    def _finish(db: Session, res: dict, bundle, ms: float) -> dict:
        ids = [it["movie_id"] for it in res["items"]]
        movies = {m.id: m for m in db.scalars(select(Movie).where(Movie.id.in_(ids)))} if ids else {}
        items = []
        for it in res["items"]:
            m = movies.get(it["movie_id"])
            if m is None:  # phim có trong mô hình nhưng không còn trong DB: bỏ qua
                continue
            items.append({**{k: v for k, v in it.items() if k != "movie_id"}, "movie": movie_json(m)})
        return {
            "model_version": bundle.version,
            "profile_size": res["profile_size"],
            "n_candidates": res["n_candidates"],
            "source_summary": res["source_summary"],
            "min_item_ratings": bundle.min_item_ratings,
            "latency_ms": round(ms, 2),
            "items": items,
            "message": res["message"],
        }


def movie_json(m: Movie, my_rating: int | None = None, stats: tuple | None = None) -> dict:
    out = {"id": m.id, "title": m.title, "year": m.year, "genres": sorted(g.name for g in m.genres)}
    if stats is not None:
        out["avg_rating_train"], out["n_ratings_train"] = stats
    if my_rating is not None:
        out["my_rating"] = my_rating
    return out
