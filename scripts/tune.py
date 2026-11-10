"""Giai đoạn 3a: grid search trên VALIDATION, chốt cấu hình và ghi configs/model.yaml.

    python scripts/tune.py --grid configs/grid.yaml
Test KHÔNG được đọc ở bước này.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from ml.data.load import load_yaml  # noqa: E402
from ml.data.split import SPLIT_NAMES  # noqa: E402
from ml.eval.tune import choose_item_threshold, run_grid, select_best, tune_k_for_competitor  # noqa: E402
from ml.models.knn import KNNModel  # noqa: E402

HEADER = """# Cấu hình KNNBaseline đã CHỐT bằng scripts/tune.py trên VALIDATION (không dùng test).
# Sinh tự động — chạy lại tune.py để cập nhật; đừng sửa tay nếu muốn tái lập.
"""


def write_threshold(model_cfg: dict, train, val, catalog, grid: dict, reports: Path) -> None:
    """Fit mô hình đã chốt, chọn min_item_ratings trên validation, ghi configs/model.yaml."""
    b, s, kn = model_cfg["baseline"], model_cfg["similarity"], model_cfg["knn"]
    model = KNNModel("baseline", k=kn["k"], min_k=kn["min_k"], shrinkage=s["shrinkage"], min_support=s["min_support"],
                     n_epochs=b["n_epochs"], reg_u=b["reg_u"], reg_i=b["reg_i"]).fit(train)
    share = grid.get("min_candidate_share", 0.25)
    t, table = choose_item_threshold(model, val, train, catalog, grid["min_item_ratings"], min_candidate_share=share)
    table.to_csv(reports / "threshold_tuning.csv", index=False)
    model_cfg["serving"]["min_item_ratings"] = t
    model_cfg["threshold_selection_rule"] = (
        f"max NDCG@10 on validation (KNNBaseline đã chốt) với ràng buộc giữ >= {share:.0%} danh mục làm ứng viên; hòa → ngưỡng nhỏ hơn"
    )
    (ROOT / "configs/model.yaml").write_text(HEADER + yaml.safe_dump(model_cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"      Ngưỡng chốt: min_item_ratings = {t}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="configs/grid.yaml")
    ap.add_argument("--only-threshold", action="store_true", help="chỉ chọn lại ngưỡng, giữ cấu hình KNN trong model.yaml")
    args = ap.parse_args()

    grid = load_yaml(ROOT / args.grid)
    data_cfg = load_yaml(ROOT / "configs/data.yaml")
    processed = ROOT / data_cfg["paths"]["processed_dir"]
    train = pd.read_csv(processed / "train.csv")
    val = pd.read_csv(processed / "validation.csv")  # cố ý không nạp test
    catalog = sorted(pd.read_csv(processed / "movies.csv")["movie_id"])
    reports = ROOT / data_cfg["paths"]["report_dir"]
    (reports / "figs").mkdir(parents=True, exist_ok=True)

    if args.only_threshold:
        model_cfg = load_yaml(ROOT / "configs/model.yaml")
        print("Chỉ chọn lại ngưỡng min_item_ratings (giữ cấu hình KNN đã chốt)")
        write_threshold(model_cfg, train, val, catalog, grid, reports)
        return 0

    n_cfg = len(grid["k"]) * len(grid["min_k"]) * len(grid["reg"]) * len(grid["n_epochs"]) * len(grid["shrinkage"]) * len(grid["min_support"])
    print(f"[1/3] Grid search: {n_cfg} cấu hình trên validation")
    results = run_grid(train, val, grid)

    print("[2/3] Chọn cấu hình (RMSE, hòa thì NDCG@10)")
    cfg, results = select_best(results, train, val, catalog)
    results.to_csv(reports / "tuning.csv", index=False)
    print("      Cấu hình chốt:", cfg)

    print("[3/3] Chọn k cho hai mô hình đối chứng")
    k_basic, curve_basic = tune_k_for_competitor("basic", cfg, train, val, grid["k"], 0.0)
    k_noshr, curve_noshr = tune_k_for_competitor("baseline", cfg, train, val, grid["k"], 0.0)
    print(f"      KNNBasic k={k_basic}; KNNBaseline(shrinkage=0) k={k_noshr}")

    model_cfg = {
        "algorithm": "knn_baseline",
        "user_based": True,
        "baseline": {"method": "als", "n_epochs": cfg["n_epochs"], "reg_u": cfg["reg_u"], "reg_i": cfg["reg_i"]},
        "similarity": {"name": "pearson_baseline", "shrinkage": cfg["shrinkage"], "min_support": cfg["min_support"]},
        "knn": {"k": cfg["k"], "min_k": cfg["min_k"]},
        "competitors": {"knn_basic": {"k": k_basic}, "knn_baseline_no_shrinkage": {"k": k_noshr}},
        "serving": {"top_n": 10, "max_n": 50, "popular_bayes_m": 20},
        "selected_on": "validation",
        "selection_rule": "min RMSE (round 4); tie -> max NDCG@10 among top-3 by RMSE",
        "split_hash": json.load(open(processed / "split_manifest.json", encoding="utf-8"))["split_hash"],
    }
    write_threshold(model_cfg, train, val, catalog, grid, reports)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    sub = results[(results.reg_u == cfg["reg_u"]) & (results.reg_i == cfg["reg_i"]) & (results.min_support == cfg["min_support"]) & (results.min_k == cfg["min_k"])]
    for shr, g in sub.groupby("shrinkage"):
        ax[0].plot(g["k"], g["val_rmse"], marker="o", label=f"shrinkage={shr:g}")
    ax[0].set(title="Validation RMSE theo K và shrinkage", xlabel="K", ylabel="RMSE")
    ax[0].legend()
    ax[1].plot([r["k"] for r in curve_basic], [r["val_rmse"] for r in curve_basic], marker="o", label="KNNBasic")
    ax[1].plot([r["k"] for r in curve_noshr], [r["val_rmse"] for r in curve_noshr], marker="o", label="KNNBaseline (shrinkage=0)")
    ax[1].set(title="Chọn K cho mô hình đối chứng", xlabel="K", ylabel="RMSE validation")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(reports / "figs" / "tuning.png", dpi=150)
    print("Xong. Đã ghi configs/model.yaml, artifacts/reports/tuning.csv, figs/tuning.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
