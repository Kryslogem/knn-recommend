"""Admin functions. role=admin only."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.errors import AppError
from backend.app.models import ModelVersion, Movie, Rating, TrainingJob, User
from backend.app.schemas import MoviePatch, UserPatch
from backend.app.security import require_role
from backend.app.services.recommend_service import movie_json

router = APIRouter(prefix="/admin", tags=["admin"])
ADMIN = Depends(require_role("admin"))


@router.get("/status")
def status(request: Request, _: User = ADMIN, db: Session = Depends(get_db)):
    count = lambda stmt: db.scalar(stmt) or 0  # noqa: E731
    reg = request.app.state.registry
    bundle = reg.get()
    active = db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)))
    return {
        "users": {
            "app": count(select(func.count()).select_from(User).where(User.kind == "app")),
            "movielens": count(select(func.count()).select_from(User).where(User.kind == "movielens")),
        },
        "movies": {
            "total": count(select(func.count()).select_from(Movie)),
            "hidden": count(select(func.count()).select_from(Movie).where(Movie.is_hidden.is_(True))),
        },
        "ratings": {
            "app": count(select(func.count()).select_from(Rating).where(Rating.source == "app")),
            "movielens": count(select(func.count()).select_from(Rating).where(Rating.source == "movielens")),
        },
        "model": {
            "loaded": bundle is not None,
            "version": bundle.version if bundle else None,
            "active_in_db": active.version if active else None,
            "loaded_at": reg.loaded_at.isoformat() if reg.loaded_at else None,
            "min_item_ratings": bundle.min_item_ratings if bundle else None,
        },
        "recommendations": request.app.state.recsvc.latency_summary(),
        "training_running": bool(count(select(func.count()).select_from(TrainingJob).where(TrainingJob.status.in_(["queued", "running"])))),
    }


@router.get("/users")
def users(
    q: str | None = Query(None, max_length=32),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = ADMIN,
    db: Session = Depends(get_db),
):
    stmt = select(User).where(User.kind == "app")
    if q:
        stmt = stmt.where(User.username.ilike(f"%{q.strip().lower()}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.id).limit(page_size).offset((page - 1) * page_size))
    items = [{"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat()} for u in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: UserPatch, request: Request, admin: User = ADMIN, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None or u.kind != "app":
        raise AppError(404, "user_not_found", "Account not found")
    if u.id == admin.id:
        raise AppError(400, "self_modification", "You cannot change your own role or lock your own account")
    if body.role is not None:
        u.role = body.role
    if body.is_active is not None:
        u.is_active = body.is_active
    db.commit()
    return {"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active}


@router.get("/movies")
def admin_movies(
    q: str | None = Query(None, max_length=100),
    hidden: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = ADMIN,
    db: Session = Depends(get_db),
):
    """Catalog for admins, including hidden films (unlike /movies, which only returns visible ones)."""
    stmt = select(Movie)
    if q:
        esc = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Movie.title.ilike(f"%{esc}%", escape="\\"))
    if hidden is not None:
        stmt = stmt.where(Movie.is_hidden.is_(hidden))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Movie.title).limit(page_size).offset((page - 1) * page_size))
    return {"items": [{**movie_json(m), "is_hidden": m.is_hidden} for m in rows], "total": total, "page": page, "page_size": page_size}


@router.patch("/movies/{movie_id}")
def patch_movie(movie_id: int, body: MoviePatch, request: Request, _: User = ADMIN, db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if m is None:
        raise AppError(404, "movie_not_found", "Film not found")
    if body.title is not None:
        m.title = body.title.strip()
    if body.is_hidden is not None:
        m.is_hidden = body.is_hidden
    db.commit()
    request.app.state.recsvc.clear()  # hiding or showing a film changes every recommendation list
    return {**movie_json(m), "is_hidden": m.is_hidden}


@router.get("/recommendations/movielens/{ml_user_id}")
def movielens_recs(
    ml_user_id: int, request: Request, n: int = Query(10, ge=1, le=50), _: User = ADMIN, db: Session = Depends(get_db)
):
    """Recommendations for one MovieLens profile (real training history), for demonstration. The profile is excluded from its own neighbours."""
    u = db.scalar(select(User).where(User.ml_user_id == ml_user_id))
    if u is None:
        raise AppError(404, "user_not_found", "No such MovieLens profile (IDs 1-943)")
    out = request.app.state.recsvc.recommend_for(db, u.id, n, exclude_user_id=ml_user_id, use_cache=False)
    return {**out, "ml_user_id": ml_user_id}
