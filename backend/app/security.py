"""Băm mật khẩu (argon2), JWT và phân quyền theo vai trò. Vai trò luôn đọc từ DB, không tin token."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.errors import AppError
from backend.app.models import User

_hasher = PasswordHash.recommended()
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")
_bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Luôn tốn thời gian băm như nhau, kể cả khi user không tồn tại (tránh dò username qua thời gian)."""
    return _hasher.verify(password, password_hash or _DUMMY_HASH) and password_hash is not None


def create_token(user_id: int, secret: str, expire_minutes: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, secret, algorithm=ALGORITHM)


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise AppError(401, "not_authenticated", "Not signed in")
    try:
        payload = jwt.decode(creds.credentials, request.app.state.settings.jwt_secret, algorithms=[ALGORITHM])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise AppError(401, "invalid_token", "Your session is invalid or has expired") from None
    if user is None or user.password_hash is None:
        raise AppError(401, "invalid_token", "Your session is invalid or has expired")
    if not user.is_active:
        raise AppError(403, "account_disabled", "This account is locked")
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "forbidden", "You do not have permission to do this")
        return user

    return dep
