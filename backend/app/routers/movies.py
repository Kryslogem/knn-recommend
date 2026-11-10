from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.errors import AppError
from backend.app.models import Genre, Movie, Rating, User, movie_genres
from backend.app.security import get_current_user
from backend.app.services.recommend_service import movie_json

router = APIRouter(tags=["movies"])


def _my_ratings(db: Session, user_id: int, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    return {m: r for m, r in db.execute(select(Rating.movie_id, Rating.rating).where(Rating.user_id == user_id, Rating.movie_id.in_(ids)))}


@router.get("/genres")
def genres(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": list(db.scalars(select(Genre.name).order_by(Genre.name)))}


@router.get("/movies")
def list_movies(
    request: Request,
    q: str | None = Query(None, max_length=100),
    genre: str | None = Query(None, max_length=40),
    year_from: int | None = Query(None, ge=1800, le=2100),
    year_to: int | None = Query(None, ge=1800, le=2100),
    sort: Literal["title", "year_desc", "year_asc", "popular"] = "title",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reg = request.app.state.registry
    stmt = select(Movie.id, Movie.title, Movie.year).where(Movie.is_hidden.is_(False))
    if q:
        esc = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Movie.title.ilike(f"%{esc}%", escape="\\"))
    if genre:
        stmt = stmt.where(Movie.id.in_(select(movie_genres.c.movie_id).join(Genre).where(Genre.name == genre)))
    if year_from is not None:
        stmt = stmt.where(Movie.year >= year_from)
    if year_to is not None:
        stmt = stmt.where(Movie.year <= year_to)
    rows = db.execute(stmt).all()
    if sort == "popular":
        rows.sort(key=lambda r: (-reg.movie_stats(r.id)[1], r.title))
    elif sort == "year_desc":
        rows.sort(key=lambda r: (-(r.year or 0), r.title))
    elif sort == "year_asc":
        rows.sort(key=lambda r: ((r.year or 9999), r.title))
    else:
        rows.sort(key=lambda r: r.title.lower())
    total = len(rows)
    ids = [r.id for r in rows[(page - 1) * page_size : page * page_size]]
    movies = {m.id: m for m in db.scalars(select(Movie).where(Movie.id.in_(ids)))} if ids else {}
    mine = _my_ratings(db, user.id, ids)
    items = [movie_json(movies[i], mine.get(i), reg.movie_stats(i)) for i in ids]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/movies/popular")
def popular(
    request: Request,
    n: int = Query(12, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Popular films (Bayesian-smoothed, from train) for onboarding. Excludes films I have rated."""
    bundle = request.app.state.registry.get()
    if bundle is None:
        raise AppError(503, "model_not_loaded", "No model is active yet")
    hidden = set(db.scalars(select(Movie.id).where(Movie.is_hidden.is_(True))))
    rated = set(db.scalars(select(Rating.movie_id).where(Rating.user_id == user.id)))
    top = bundle.popular.top_n(n, hidden | rated)
    movies = {m.id: m for m in db.scalars(select(Movie).where(Movie.id.in_([m for m, _ in top])))}
    reg = request.app.state.registry
    items = [
        {**movie_json(movies[m], None, reg.movie_stats(m)), "popularity_score": round(s, 4)} for m, s in top if m in movies
    ]
    return {"items": items, "model_version": bundle.version}


@router.get("/movies/{movie_id}")
def movie_detail(movie_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if m is None or m.is_hidden:
        raise AppError(404, "movie_not_found", "Film not found")
    reg = request.app.state.registry
    out = movie_json(m, _my_ratings(db, user.id, [m.id]).get(m.id), reg.movie_stats(m.id))
    out.setdefault("my_rating", None)
    out.update({"release_date": m.release_date, "imdb_url": m.imdb_url})
    return out


@router.get("/movies/{movie_id}/prediction")
def movie_prediction(movie_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Predicted rating for me plus an explanation (U09)."""
    m = db.get(Movie, movie_id)
    if m is None or m.is_hidden:
        raise AppError(404, "movie_not_found", "Film not found")
    return request.app.state.recsvc.predict_one(db, user.id, movie_id)
