from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.errors import AppError
from backend.app.models import Rating, User
from backend.app.schemas import Credentials
from backend.app.security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def user_json(db: Session, u: User) -> dict:
    n = db.scalar(select(func.count()).select_from(Rating).where(Rating.user_id == u.id)) or 0
    return {"id": u.id, "username": u.username, "role": u.role, "n_ratings": n}


def _token(request: Request, db: Session, u: User) -> dict:
    s = request.app.state.settings
    return {"access_token": create_token(u.id, s.jwt_secret, s.jwt_expire_minutes), "token_type": "bearer", "user": user_json(db, u)}


@router.post("/register", status_code=201)
def register(body: Credentials, request: Request, db: Session = Depends(get_db)):
    """Tạo tài khoản vai trò `user`. Chỉ thu username (tên giả danh) + mật khẩu."""
    if db.scalar(select(User.id).where(User.username == body.username)):
        raise AppError(409, "username_taken", "Tên đăng nhập đã tồn tại")
    u = User(username=body.username, password_hash=hash_password(body.password), role="user", kind="app")
    db.add(u)
    try:
        db.commit()
    except IntegrityError:  # hai yêu cầu đăng ký cùng lúc
        db.rollback()
        raise AppError(409, "username_taken", "Tên đăng nhập đã tồn tại") from None
    return _token(request, db, u)


@router.post("/login")
def login(body: Credentials, request: Request, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.username == body.username))
    ok = verify_password(body.password, u.password_hash if u else None)
    if not ok or u is None:
        raise AppError(401, "bad_credentials", "Sai tên đăng nhập hoặc mật khẩu")
    if not u.is_active:
        raise AppError(403, "account_disabled", "Tài khoản đã bị khóa")
    return _token(request, db, u)


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_json(db, user)
