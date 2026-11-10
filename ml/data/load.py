"""Đọc các file gốc MovieLens 100K thành DataFrame."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

RATING_COLUMNS = ["user_id", "movie_id", "rating", "timestamp"]
ITEM_BASE_COLUMNS = ["movie_id", "title", "release_date", "video_release_date", "imdb_url"]


def load_yaml(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_ratings(path: str | Path) -> pd.DataFrame:
    """`u.data`: phân cách tab, 4 cột, không header."""
    return pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=RATING_COLUMNS,
        dtype={"user_id": "int64", "movie_id": "int64", "rating": "int64", "timestamp": "int64"},
    )


def load_genres(path: str | Path) -> list[str]:
    """`u.genre`: dòng `name|id`; trả danh sách tên theo đúng thứ tự id."""
    rows = []
    with open(path, encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            name, gid = line.rsplit("|", 1)
            rows.append((int(gid), name))
    rows.sort()
    if [g for g, _ in rows] != list(range(len(rows))):
        raise ValueError("u.genre: id thể loại không liên tục từ 0")
    return [name for _, name in rows]


def load_items(path: str | Path, genres: list[str], encoding: str = "latin-1") -> pd.DataFrame:
    """`u.item`: phân cách '|', encoding latin-1, 5 cột thông tin + 1 cờ cho mỗi thể loại."""
    df = pd.read_csv(
        path,
        sep="|",
        header=None,
        names=ITEM_BASE_COLUMNS + genres,
        encoding=encoding,
        dtype={"movie_id": "int64"},
    )
    year_from_title = df["title"].str.extract(r"\((\d{4})\)\s*$")[0]
    year_from_date = pd.to_datetime(df["release_date"], format="%d-%b-%Y", errors="coerce").dt.year
    df["year"] = pd.to_numeric(year_from_title, errors="coerce").fillna(year_from_date).astype("Int64")
    df["genres"] = df[genres].apply(lambda row: [g for g in genres if row[g] == 1], axis=1)
    return df


def load_movielens(raw_dir: str | Path, files: dict) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    raw_dir = Path(raw_dir)
    genres = load_genres(raw_dir / files["genres"])
    ratings = load_ratings(raw_dir / files["ratings"])
    items = load_items(raw_dir / files["items"], genres, files.get("item_encoding", "latin-1"))
    return ratings, items, genres
