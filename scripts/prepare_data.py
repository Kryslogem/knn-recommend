"""Giai đoạn 1: tải → kiểm tra → làm sạch → chia MovieLens 100K.

Chạy từ thư mục gốc dự án:
    python scripts/prepare_data.py --config configs/data.yaml

Đầu ra:
    data/raw/ml-100k/                      dữ liệu gốc (không commit)
    data/processed/{train,validation,test}.csv
    data/processed/movies.csv              danh mục phim đã chuẩn hóa (cho seed DB)
    data/processed/split_manifest.json     seed, tỉ lệ, kích thước, SHA-256
    artifacts/reports/data_report.json     kết quả kiểm tra + EDA
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Console Windows mặc định cp1252 không in được tiếng Việt.
for _stream in (sys.stdout, sys.stderr):
    _stream.reconfigure(encoding="utf-8")

from ml.data.download import fetch_movielens, sha256_file  # noqa: E402
from ml.data.load import load_movielens, load_yaml  # noqa: E402
from ml.data.split import split_per_user, write_split  # noqa: E402
from ml.data.validate import clean_ratings, validate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/data.yaml")
    args = parser.parse_args(argv)

    cfg = load_yaml(ROOT / args.config)
    paths = {k: ROOT / v for k, v in cfg["paths"].items()}
    split_cfg = cfg["split"]

    print(f"[1/4] Tải dữ liệu từ {cfg['source']['url']}")
    source = fetch_movielens(cfg["source"]["url"], paths["raw_dir"], cfg["source"].get("sha256"))
    print(f"      SHA-256 zip: {source['zip_sha256']} (đã đối chiếu cấu hình: {source['checksum_verified']})")

    raw = Path(source["extracted_dir"])
    if not raw.is_absolute():
        raw = ROOT / raw
    ratings, items, genres = load_movielens(raw, cfg["files"])
    u_data_sha = sha256_file(raw / cfg["files"]["ratings"])

    print("[2/4] Kiểm tra chất lượng dữ liệu")
    report = validate(ratings, items, cfg["expected"])
    for c in report["checks"]:
        mark = "OK " if c["passed"] else ("ERR" if c["severity"] == "error" else "WRN")
        print(f"      [{mark}] {c['name']}")
    ratings_clean, n_dropped = clean_ratings(ratings)
    report["cleaning"] = {"duplicate_rows_dropped": n_dropped, "rows_after_cleaning": len(ratings_clean)}
    report["source"] = {**cfg["source"], **source, "u_data_sha256": u_data_sha}
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    paths["report_dir"].mkdir(parents=True, exist_ok=True)
    report_path = paths["report_dir"] / "data_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    if not report["ok"]:
        print(f"Dữ liệu có lỗi nghiêm trọng — dừng. Xem {report_path}", file=sys.stderr)
        return 1

    print(f"[3/4] Chia dữ liệu theo người dùng (seed={split_cfg['seed']})")
    splits = split_per_user(ratings_clean, split_cfg["seed"], split_cfg["validation"], split_cfg["test"])
    manifest = write_split(
        splits,
        paths["processed_dir"],
        {
            "dataset": cfg["source"]["name"],
            "u_data_sha256": u_data_sha,
            "strategy": split_cfg["strategy"],
            "seed": split_cfg["seed"],
            "fractions": {k: split_cfg[k] for k in ("train", "validation", "test")},
            "rounding": "n_test = floor(test*n + 0.5); n_val = floor(val*n + 0.5); train = phần còn lại",
        },
    )
    for name, n in manifest["summary"]["rows"].items():
        print(f"      {name:<10} {n:>6} dòng")
    print(f"      split_hash: {manifest['split_hash']}")

    print("[4/4] Ghi danh mục phim đã chuẩn hóa")
    catalog = items[["movie_id", "title", "year", "release_date", "imdb_url"]].copy()
    catalog["genres"] = items["genres"].str.join("|")
    catalog.to_csv(paths["processed_dir"] / "movies.csv", index=False, lineterminator="\n", encoding="utf-8")

    print(f"Xong. Báo cáo: {report_path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
