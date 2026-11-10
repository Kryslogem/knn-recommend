"""Nạp artifact đang kích hoạt và đề xuất cho một hồ sơ; đo độ trễ và kiểm tra fold-in trên dữ liệu thật.

    python scripts/demo_recommend.py --ml-user 1            # hồ sơ = rating train của user MovieLens 1
    python scripts/demo_recommend.py --ratings "50:5,181:5,258:2"   # hồ sơ tự nhập movie_id:rating
    python scripts/demo_recommend.py --check                # độ trễ + kiểm tra fold-in trên mọi user train
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml.models.artifact import load_artifact  # noqa: E402
from ml.models.foldin import fold_in, recommend  # noqa: E402

models_dir = ROOT / "artifacts" / "models"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version")
    ap.add_argument("--ml-user", type=int)
    ap.add_argument("--ratings")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    version = args.version or json.loads((models_dir / "active.json").read_text())["version"]
    t0 = time.time()
    b = load_artifact(models_dir / version)
    print(f"Nạp {version} trong {time.time() - t0:.2f}s (split_hash {b.meta['split_hash'][:12]}…)")
    train = pd.read_csv(ROOT / "data/processed/train.csv")
    movies = pd.read_csv(ROOT / "data/processed/movies.csv").set_index("movie_id")
    thr = b.min_item_ratings

    if args.check:
        users = train.groupby("user_id")
        hist = {int(u): dict(zip(g.movie_id, g.rating)) for u, g in users}
        lat = []
        for u in list(hist)[:200]:
            t = time.perf_counter()
            recommend(b.knn, b.popular, hist[u], n=10, min_item_ratings=thr)
            lat.append((time.perf_counter() - t) * 1000)
        print(f"Độ trễ recommend() trên 200 hồ sơ thật: p50={np.percentile(lat, 50):.1f} ms, "
              f"p95={np.percentile(lat, 95):.1f} ms, max={max(lat):.1f} ms  (mục tiêu NFR01: < 2000 ms)")
        d = [abs(fold_in(b.knn, hist[u]).b_q - b.knn.bias.b_u[b.knn.rm.user_index[u]]) for u in hist]
        print(f"|b_q (một bước) − b_u (ALS)| trên {len(d)} user train: mean={np.mean(d):.4f}, max={np.max(d):.4f}")
        # fold-in một user train (bỏ chính họ) so với dự đoán của mô hình đã fit, cùng bias học được
        agree = []
        for u in list(hist)[:50]:
            uidx = b.knn.rm.user_index[u]
            r = recommend(b.knn, b.popular, hist[u], n=10, min_item_ratings=thr, exclude_user_id=u,
                          bias_override=b.knn.bias.b_u[uidx], with_neighbors=False)
            ids = np.array([b.knn.rm.item_index[it["movie_id"]] for it in r["items"]])
            est, _, _ = b.knn._predict_user_items(uidx, ids)
            agree.append(np.abs(est - np.array([it["predicted_rating"] for it in r["items"]])).max())
        print(f"Fold-in vs predict() của mô hình đã fit (cùng bias, 50 user): sai khác lớn nhất = {max(agree):.2e}")
        return 0

    if args.ratings:
        ratings = {int(a): int(c) for a, c in (p.split(":") for p in args.ratings.split(","))}
    elif args.ml_user:
        g = train[train.user_id == args.ml_user]
        ratings = dict(zip(g.movie_id, g.rating))
    else:
        ratings = {}
    t = time.perf_counter()
    res = recommend(b.knn, b.popular, ratings, n=args.n, min_item_ratings=thr)
    ms = (time.perf_counter() - t) * 1000
    print(f"Hồ sơ {res['profile_size']} phim, {ms:.1f} ms, nguồn: {res['source_summary']}")
    if res["message"]:
        print("Ghi chú:", res["message"])
    for i, it in enumerate(res["items"], 1):
        bd = it["breakdown"]
        why = f"μ={bd['mu']:.2f} {bd['b_user']:+.2f} {bd['b_item']:+.2f} {bd['neighbor_term']:+.2f}" if bd else "phổ biến"
        print(f"{i:>2}. {movies.loc[it['movie_id'], 'title']:<48} {it['predicted_rating']:.2f}  [{it['source']}, {it['n_neighbors']} láng giềng]  {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
