"""Schema request. Mọi đầu vào được kiểm tra miền giá trị ở đây (PLAN.md mục 12.4)."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,32}$")


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _norm(cls, v: str) -> str:
        v = v.strip().lower()  # tên đăng nhập không phân biệt hoa thường
        if not USERNAME_RE.match(v):
            raise ValueError("chỉ gồm chữ thường, số, '_', '.', '-' (3–32 ký tự)")
        return v


class RatingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: StrictInt = Field(ge=1, le=5)  # số nguyên 1–5; "5" hay 3.5 bị từ chối


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "admin", "data_scientist"] | None = None
    is_active: bool | None = None


class MoviePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_hidden: bool | None = None


class TrainRequest(BaseModel):
    """Siêu tham số huấn luyện; trường bỏ trống lấy từ configs/model.yaml."""

    model_config = ConfigDict(extra="forbid")
    k: int | None = Field(default=None, ge=1, le=200)
    min_k: int | None = Field(default=None, ge=1, le=50)
    reg_u: float | None = Field(default=None, ge=0, le=500)
    reg_i: float | None = Field(default=None, ge=0, le=500)
    n_epochs: int | None = Field(default=None, ge=1, le=50)
    shrinkage: float | None = Field(default=None, ge=0, le=5000)
    min_support: int | None = Field(default=None, ge=1, le=50)
    min_item_ratings: int | None = Field(default=None, ge=0, le=1000)
