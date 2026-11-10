"""Khởi tạo CSDL vận hành: phim, thể loại, hồ sơ MovieLens (chỉ rating TRAIN) và 3 tài khoản mẫu.

    python scripts/seed_db.py [--reset]

Mật khẩu tài khoản mẫu KHÔNG nằm trong mã: nếu KNN_SEED_*_PASSWORD trống, script sinh ngẫu nhiên và ghi vào
.env (đã bị .gitignore). Script chỉ in tên đăng nhập, không in mật khẩu — mở .env để xem.
"""

import argparse
import re
import secrets
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

ENV = ROOT / ".env"
SEED_KEYS = ["KNN_SEED_ADMIN_PASSWORD", "KNN_SEED_DS_PASSWORD", "KNN_SEED_USER_PASSWORD"]
PLACEHOLDERS = {"", "change-me-to-a-long-random-string", "dev-only-change-me"}


def ensure_env() -> list[str]:
    """Bảo đảm .env có JWT secret thật và mật khẩu mẫu; trả danh sách khóa vừa được sinh."""
    if not ENV.exists():
        shutil.copy(ROOT / ".env.example", ENV)
    text = ENV.read_text(encoding="utf-8")
    generated = []
    for key in ["KNN_JWT_SECRET", *SEED_KEYS]:
        m = re.search(rf"^{key}=(.*)$", text, re.M)
        value = m.group(1).strip() if m else ""
        if value in PLACEHOLDERS:
            new = f"{key}={secrets.token_urlsafe(32 if key == 'KNN_JWT_SECRET' else 12)}"
            text = re.sub(rf"^{key}=.*$", new, text, flags=re.M) if m else text.rstrip("\n") + f"\n{new}\n"
            generated.append(key)
    ENV.write_text(text, encoding="utf-8")
    return generated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="xóa toàn bộ bảng rồi tạo lại")
    args = ap.parse_args()

    generated = ensure_env()
    from backend.app.config import get_settings

    get_settings.cache_clear()
    s = get_settings()

    from sqlalchemy import select, text
    from sqlalchemy.orm import sessionmaker

    from backend.app.db import Base, make_engine
    from backend.app.models import Genre, Movie, Rating, User
    from backend.app.security import hash_password

    processed = s.path(s.processed_dir)
    for f in ("movies.csv", "train.csv"):
        if not (processed / f).exists():
            print(f"Thiếu {processed / f}. Chạy scripts/prepare_data.py trước.", file=sys.stderr)
            return 1
    engine = make_engine(s.database_url)
    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)

    movies = pd.read_csv(processed / "movies.csv")
    train = pd.read_csv(processed / "train.csv")
    with Session() as db:
        if db.scalar(select(Movie.id).limit(1)) is not None:
            print("CSDL đã có dữ liệu — bỏ qua phần phim/rating (dùng --reset để tạo lại).")
        else:
            names = sorted({g for gs in movies["genres"].fillna("") for g in gs.split("|") if g})
            genre_rows = {n: Genre(name=n) for n in names}
            db.add_all(genre_rows.values())
            for r in movies.itertuples():
                db.add(Movie(
                    id=int(r.movie_id), title=r.title, year=None if pd.isna(r.year) else int(r.year),
                    release_date=None if pd.isna(r.release_date) else r.release_date,
                    imdb_url=None if pd.isna(r.imdb_url) else r.imdb_url,
                    genres=[genre_rows[g] for g in (r.genres.split("|") if isinstance(r.genres, str) else [])],
                ))
            # Hồ sơ MovieLens: id = ml_user_id (1–943) nên user app mới luôn có id >= 944 (FR02). Không đăng nhập được.
            db.add_all(User(id=int(u), kind="movielens", ml_user_id=int(u), role="user", is_active=False) for u in sorted(train["user_id"].unique()))
            db.flush()
            db.execute(Rating.__table__.insert(), [
                {"user_id": int(r.user_id), "movie_id": int(r.movie_id), "rating": int(r.rating), "source": "movielens"}
                for r in train.itertuples()
            ])
            db.commit()
            print(f"Đã nạp {len(movies)} phim, {len(names)} thể loại, {train['user_id'].nunique()} hồ sơ MovieLens, {len(train)} rating (train).")

        for role, uname, pwd in (
            ("admin", s.seed_admin_username, s.seed_admin_password),
            ("data_scientist", s.seed_ds_username, s.seed_ds_password),
            ("user", s.seed_user_username, s.seed_user_password),
        ):
            u = db.scalar(select(User).where(User.username == uname))
            if u is None:
                db.add(User(username=uname, password_hash=hash_password(pwd), role=role, kind="app"))
                print(f"Đã tạo tài khoản mẫu: {uname} (vai trò {role})")
            else:
                print(f"Tài khoản {uname} đã tồn tại — giữ nguyên.")
        db.commit()
    if generated:
        print(f"Đã sinh {len(generated)} giá trị bí mật mới trong {ENV.name} (không hiển thị). Mở file để xem mật khẩu mẫu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
