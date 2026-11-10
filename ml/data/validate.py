"""Kiểm tra chất lượng dữ liệu và thống kê khám phá (EDA).

Quy tắc xử lý (ghi vào báo cáo):
- Rating ngoài miền [min, max] hoặc thiếu giá trị: lỗi nghiêm trọng, pipeline dừng.
- movie_id không có trong danh mục: lỗi nghiêm trọng, pipeline dừng.
- Trùng cặp (user_id, movie_id): giữ bản ghi có timestamp mới nhất (xem `clean_ratings`).
- Phim trùng tên: chỉ cảnh báo; giữ nguyên vì movie_id khác nhau.
- Ô chưa đánh giá là THIẾU, không bao giờ điền 0.
"""

from __future__ import annotations

import pandas as pd


def _check(name: str, passed: bool, detail, severity: str = "error") -> dict:
    return {"name": name, "passed": bool(passed), "severity": severity, "detail": detail}


def clean_ratings(ratings: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Bỏ trùng cặp (user, movie), giữ timestamp mới nhất. Trả (df, số dòng đã bỏ)."""
    before = len(ratings)
    out = (
        ratings.sort_values(["user_id", "movie_id", "timestamp"])
        .drop_duplicates(["user_id", "movie_id"], keep="last")
        .sort_values(["user_id", "movie_id"])
        .reset_index(drop=True)
    )
    return out, before - len(out)


def _describe(counts: pd.Series) -> dict:
    return {
        "min": int(counts.min()),
        "p25": float(counts.quantile(0.25)),
        "median": float(counts.median()),
        "mean": round(float(counts.mean()), 3),
        "p75": float(counts.quantile(0.75)),
        "max": int(counts.max()),
    }


def validate(ratings: pd.DataFrame, items: pd.DataFrame, expected: dict) -> dict:
    """Chạy các kiểm tra; trả về báo cáo. `report["ok"]` False nếu có lỗi nghiêm trọng."""
    rmin, rmax = expected["rating_min"], expected["rating_max"]
    checks = []

    missing_r = int(ratings.isna().sum().sum())
    checks.append(_check("ratings_no_missing", missing_r == 0, {"missing_cells": missing_r}))

    out_of_range = int((~ratings["rating"].between(rmin, rmax)).sum())
    checks.append(_check("rating_in_range", out_of_range == 0, {"out_of_range_rows": out_of_range, "range": [rmin, rmax]}))

    non_integer = int((ratings["rating"] != ratings["rating"].round()).sum())
    checks.append(_check("rating_integer", non_integer == 0, {"non_integer_rows": non_integer}))

    dup_pairs = int(ratings.duplicated(["user_id", "movie_id"]).sum())
    checks.append(
        _check("unique_user_movie_pair", dup_pairs == 0, {"duplicate_rows": dup_pairs, "rule": "keep latest timestamp"}, "warning")
    )

    catalog = set(items["movie_id"])
    orphans = sorted(set(ratings["movie_id"]) - catalog)
    checks.append(_check("movie_ids_in_catalog", not orphans, {"orphan_movie_ids": orphans[:20], "count": len(orphans)}))

    dup_item_ids = int(items["movie_id"].duplicated().sum())
    checks.append(_check("unique_movie_id_in_catalog", dup_item_ids == 0, {"duplicate_ids": dup_item_ids}))

    dup_titles = items[items["title"].duplicated(keep=False)].sort_values("title")
    checks.append(
        _check(
            "unique_movie_title",
            dup_titles.empty,
            {"count": int(dup_titles["title"].nunique()), "examples": dup_titles[["movie_id", "title"]].head(10).to_dict("records")},
            "warning",
        )
    )

    no_genre = int((items["genres"].str.len() == 0).sum())
    checks.append(_check("movie_has_genre", no_genre == 0, {"movies_without_genre": no_genre}, "warning"))

    missing_year = int(items["year"].isna().sum())
    checks.append(_check("movie_has_year", missing_year == 0, {"movies_without_year": missing_year}, "warning"))

    n_users = int(ratings["user_id"].nunique())
    n_rated_items = int(ratings["movie_id"].nunique())
    n_ratings = len(ratings)
    counts_ok = (
        n_users == expected["n_users"] and len(items) == expected["n_items"] and n_ratings == expected["n_ratings"]
    )
    checks.append(
        _check(
            "counts_match_u_info",
            counts_ok,
            {
                "users": [n_users, expected["n_users"]],
                "items": [len(items), expected["n_items"]],
                "ratings": [n_ratings, expected["n_ratings"]],
            },
        )
    )

    per_user = ratings.groupby("user_id").size()
    per_item = ratings.groupby("movie_id").size()
    sparsity = 1 - n_ratings / (n_users * len(items))

    stats = {
        "n_users": n_users,
        "n_items_catalog": len(items),
        "n_items_rated": n_rated_items,
        "n_ratings": n_ratings,
        "sparsity": round(sparsity, 5),
        "rating_mean": round(float(ratings["rating"].mean()), 4),
        "rating_std": round(float(ratings["rating"].std()), 4),
        "rating_distribution": {int(k): int(v) for k, v in ratings["rating"].value_counts().sort_index().items()},
        "ratings_per_user": _describe(per_user),
        "ratings_per_item": _describe(per_item),
        "items_with_lt_5_ratings": int((per_item < 5).sum()),
        "items_with_1_rating": int((per_item == 1).sum()),
        "top10_items_share_of_ratings": round(float(per_item.nlargest(10).sum() / n_ratings), 4),
        "timestamp_range_utc": [
            str(pd.to_datetime(ratings["timestamp"].min(), unit="s")),
            str(pd.to_datetime(ratings["timestamp"].max(), unit="s")),
        ],
        "genre_counts": items.explode("genres")["genres"].value_counts().to_dict(),
    }

    ok = all(c["passed"] for c in checks if c["severity"] == "error")
    return {"ok": ok, "checks": checks, "stats": stats}
