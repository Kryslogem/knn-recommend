from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.errors import AppError
from backend.app.models import Genre, Movie, User
from backend.app.security import get_current_user

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
def my_recommendations(
    request: Request,
    n: int = Query(10, ge=1, le=50),
    genre: str | None = Query(None, max_length=40),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Top-N cho tôi, tính bằng mô hình KNNBaseline thật từ các điểm hiện hành của tôi."""
    if genre is not None and db.scalar(select(Genre.id).where(Genre.name == genre)) is None:
        raise AppError(422, "unknown_genre", f"Thể loại không tồn tại: {genre}")
    return request.app.state.recsvc.recommend_for(db, user.id, n, genre)


@router.get("/{movie_id}/explain")
def explain(movie_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Giải thích điểm dự đoán cho một phim: phân rã μ + b_user + b_item + phần láng giềng, và các láng giềng chính."""
    m = db.get(Movie, movie_id)
    if m is None or m.is_hidden:
        raise AppError(404, "movie_not_found", "Không tìm thấy phim")
    return request.app.state.recsvc.predict_one(db, user.id, movie_id)
