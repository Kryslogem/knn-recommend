from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.errors import AppError
from backend.app.models import Movie, Rating, User, utcnow
from backend.app.schemas import RatingIn
from backend.app.security import get_current_user
from backend.app.services.recommend_service import movie_json

router = APIRouter(prefix="/ratings", tags=["ratings"])


def _visible_movie(db: Session, movie_id: int) -> Movie:
    m = db.get(Movie, movie_id)
    if m is None or m.is_hidden:
        raise AppError(404, "movie_not_found", "Không tìm thấy phim")
    return m


@router.get("/me")
def my_ratings(
    sort: Literal["recent", "rating_desc", "rating_asc", "title"] = "recent",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    base = select(Rating, Movie).join(Movie, Movie.id == Rating.movie_id).where(Rating.user_id == user.id)
    order = {
        "recent": (Rating.updated_at.desc(), Rating.id.desc()),
        "rating_desc": (Rating.rating.desc(), Movie.title),
        "rating_asc": (Rating.rating.asc(), Movie.title),
        "title": (Movie.title,),
    }[sort]
    total = db.scalar(select(func.count()).select_from(Rating).where(Rating.user_id == user.id)) or 0
    rows = db.execute(base.order_by(*order).limit(page_size).offset((page - 1) * page_size)).all()
    items = [{"rating": r.rating, "updated_at": r.updated_at.isoformat(), "movie": movie_json(m)} for r, m in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/{movie_id}")
def put_rating(movie_id: int, body: RatingIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tạo hoặc cập nhật (upsert, idempotent): mỗi cặp user–phim có đúng một điểm hiện hành."""
    _visible_movie(db, movie_id)
    row = db.scalar(select(Rating).where(Rating.user_id == user.id, Rating.movie_id == movie_id))
    created = row is None
    if created:
        row = Rating(user_id=user.id, movie_id=movie_id, rating=body.rating, source="app")
        db.add(row)
    elif row.rating != body.rating:
        row.rating, row.updated_at = body.rating, utcnow()
    db.commit()
    request.app.state.recsvc.invalidate_user(user.id)  # NFR03: cập nhật điểm làm mới cache đề xuất
    return {"movie_id": movie_id, "rating": row.rating, "created": created, "updated_at": row.updated_at.isoformat()}


@router.delete("/{movie_id}")
def delete_rating(movie_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Rating).where(Rating.user_id == user.id, Rating.movie_id == movie_id))
    if row is None:
        raise AppError(404, "rating_not_found", "Bạn chưa chấm phim này")
    db.delete(row)
    db.commit()
    request.app.state.recsvc.invalidate_user(user.id)
    return {"movie_id": movie_id, "deleted": True}
