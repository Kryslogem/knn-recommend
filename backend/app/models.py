"""Bảng cơ sở dữ liệu (PLAN.md mục 6)."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # UTC, không múi giờ (SQLite)


movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str | None] = mapped_column(String(32), unique=True)  # null với user MovieLens
    password_hash: Mapped[str | None] = mapped_column(String(255))  # null → không đăng nhập được
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin | data_scientist
    kind: Mapped[str] = mapped_column(String(12), default="app")  # app | movielens
    ml_user_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (CheckConstraint("role IN ('user','admin','data_scientist')", name="ck_user_role"),)


class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)


class Movie(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)  # = movie_id của MovieLens
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[int | None] = mapped_column(Integer)
    release_date: Mapped[str | None] = mapped_column(String(20))
    imdb_url: Mapped[str | None] = mapped_column(String(500))
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    genres: Mapped[list[Genre]] = relationship(secondary=movie_genres, lazy="selectin")


class Rating(Base):
    __tablename__ = "ratings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(12), default="app")  # movielens | app
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_rating_user_movie"),  # một điểm hiện hành mỗi cặp
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating_range"),
        Index("ix_ratings_user", "user_id"),
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(120), unique=True)
    algorithm: Mapped[str] = mapped_column(String(40))
    config: Mapped[dict] = mapped_column(JSON)
    data_hash: Mapped[str | None] = mapped_column(String(64))
    split_hash: Mapped[str | None] = mapped_column(String(64))
    artifact_path: Mapped[str] = mapped_column(String(500))
    metrics_val: Mapped[dict | None] = mapped_column(JSON)
    metrics_test: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    includes_app_ratings: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrainingJob(Base):
    __tablename__ = "training_jobs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(12), default="queued")  # queued|running|succeeded|failed
    config: Mapped[dict] = mapped_column(JSON)
    log: Mapped[str] = mapped_column(Text, default="")
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
