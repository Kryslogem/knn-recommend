"""Giai đoạn 3b: đánh giá cuối 5 mô hình trên validation + TEST (cấu hình đã chốt bởi tune.py).

    python scripts/evaluate.py
Test chỉ nên chạy MỘT lần cho một cấu hình: script từ chối chạy lại nếu comparison.json đã có cùng
config_hash, trừ khi có --force (khi đó ghi nhận trong log).
"""

import argparse
import hashlib
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

from ml.data.load import load_yaml  # noqa: E402
from ml.eval.error_analysis import analyze  # noqa: E402
from ml.eval.evaluate import evaluate_model  # noqa: E402
from ml.models.baseline import BiasOnlyModel  # noqa: E402
from ml.models.knn import KNNModel  # noqa: E402
from ml.models.popular import PopularModel  # noqa: E402

MODEL_LABELS = {
    "popular": "1. Popular films",
    "bias_only": "2. Bias-only",
    "knn_basic": "3. KNNBasic (plain Pearson)",
    "knn_baseline_no_shrinkage": "4. KNNBaseline, no shrinkage",
    "knn_baseline": "5. KNNBaseline (full)",
}
METRIC_COLS = ["rmse", "mae", "rmse_knn_supported", "precision@10", "recall@10", "ndcg@10",
               "prediction_coverage_knn", "fallback_rate", "catalog_coverage", "n_eligible_users", "n_pairs"]


def build_models(cfg: dict) -> dict:
    b, s, kn, comp = cfg["baseline"], cfg["similarity"], cfg["knn"], cfg["competitors"]
    common = dict(min_support=s["min_support"], n_epochs=b["n_epochs"], reg_u=b["reg_u"], reg_i=b["reg_i"])
    return {
        "popular": PopularModel(cfg["serving"]["popular_bayes_m"]),
        "bias_only": BiasOnlyModel(b["n_epochs"], b["reg_u"], b["reg_i"]),
        "knn_basic": KNNModel("basic", k=comp["knn_basic"]["k"], min_k=kn["min_k"], shrinkage=0.0, **common),
        "knn_baseline_no_shrinkage": KNNModel(
            "baseline", k=comp["knn_baseline_no_shrinkage"]["k"], min_k=kn["min_k"], shrinkage=0.0, **common),
        "knn_baseline": KNNModel("baseline", k=kn["k"], min_k=kn["min_k"], shrinkage=s["shrinkage"], **common),
    }


def write_error_figure(errors: dict, reports) -> None:
    fig, ax = plt.subplots(1, 3, figsize=(16, 4))
    for a, key, title in zip(ax, ["by_user_activity", "by_item_popularity", "by_true_rating"],
                             ["RMSE by user activity", "RMSE by film popularity", "RMSE by true rating"]):
        g = pd.DataFrame(errors[key]).set_index("group")
        g[["rmse_knn_baseline", "rmse_bias_only"]].plot.bar(ax=a, rot=15, color=["#111111", "#8a8a84"])
        a.set_title(title + " (test)")
        a.set_xlabel("")
    fig.tight_layout()
    fig.savefig(reports / "figs" / "error_analysis.png", dpi=150)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="allow re-running the test set for the same configuration")
    ap.add_argument("--errors-only", action="store_true",
                    help="regenerate only error_analysis.json and its figure (no ranking metrics, comparison files untouched)")
    args = ap.parse_args()

    cfg_path = ROOT / "configs/model.yaml"
    cfg = load_yaml(cfg_path)
    data_cfg = load_yaml(ROOT / "configs/data.yaml")
    processed = ROOT / data_cfg["paths"]["processed_dir"]
    reports = ROOT / data_cfg["paths"]["report_dir"]
    (reports / "figs").mkdir(parents=True, exist_ok=True)

    manifest = json.load(open(processed / "split_manifest.json", encoding="utf-8"))
    if cfg.get("split_hash") != manifest["split_hash"]:
        print("model.yaml was chosen on a different split than the current one. Re-run scripts/tune.py.", file=sys.stderr)
        return 1
    if args.errors_only:
        train, test = (pd.read_csv(processed / f"{n}.csv") for n in ("train", "test"))
        movies = pd.read_csv(processed / "movies.csv")
        models = build_models(cfg)
        preds = {}
        for name in ("knn_baseline", "bias_only"):
            models[name].fit(train)
            preds[name] = test.join(models[name].predict_frame(test))
        errors = analyze(preds, "knn_baseline", train, movies)
        json.dump(errors, open(reports / "error_analysis.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        write_error_figure(errors, reports)
        print("Done: error_analysis.json and figs/error_analysis.png regenerated (predictions are deterministic).")
        return 0
    config_hash = hashlib.sha256(cfg_path.read_bytes()).hexdigest()[:16]
    out_json = reports / "comparison.json"
    if out_json.exists() and not args.force:
        if json.load(open(out_json, encoding="utf-8")).get("config_hash") == config_hash:
            print("The test set was already evaluated for this configuration (same config_hash). Use --force to re-run.", file=sys.stderr)
            return 1

    train, val, test = (pd.read_csv(processed / f"{n}.csv") for n in ("train", "validation", "test"))
    movies = pd.read_csv(processed / "movies.csv")
    catalog = sorted(movies["movie_id"])

    thr = int(cfg["serving"]["min_item_ratings"])
    rows, test_preds = [], {}
    for name, model in build_models(cfg).items():
        print(f"== {MODEL_LABELS[name]}")
        model.fit(train)
        for split, held, extra in (("validation", val, None), ("test", test, val)):
            m, preds = evaluate_model(model, held, train, catalog, extra_exclude=extra, min_item_ratings=thr)
            rows.append({"model": name, "label": MODEL_LABELS[name], "split": split, "min_item_ratings": thr, **m})
            if split == "test":
                test_preds[name] = preds
            print(f"   {split:<10} RMSE={m['rmse']:.4f} MAE={m['mae']:.4f} | unfiltered: R@10={m['recall@10']:.4f} "
                  f"NDCG@10={m['ndcg@10']:.4f} | filtered >={thr}: R@10={m[f'recall@10_min{thr}']:.4f} "
                  f"NDCG@10={m[f'ndcg@10_min{thr}']:.4f} cov={m[f'catalog_coverage_min{thr}']:.3f} | knn={m['prediction_coverage_knn']:.3f}")

    table = pd.DataFrame(rows)
    table.to_csv(reports / "comparison.csv", index=False)
    errors = analyze(
        {k: test_preds[k] for k in ("knn_baseline", "bias_only")}, "knn_baseline", train, movies)
    json.dump(errors, open(reports / "error_analysis.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(
        {"config_hash": config_hash, "split_hash": manifest["split_hash"], "forced_rerun": bool(args.force),
         "config": cfg, "rows": rows},
        open(out_json, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    t = table[table["split"] == "test"].set_index("model").loc[list(MODEL_LABELS)]
    fig, ax = plt.subplots(1, 3, figsize=(16, 4))
    for a, col in zip(ax, ["rmse", f"ndcg@10_min{thr}", f"recall@10_min{thr}"]):
        a.barh([MODEL_LABELS[m] for m in t.index], t[col], color="#111111")
        a.invert_yaxis(); a.set_title(f"{col} (test)")
        for y, v in enumerate(t[col]):
            a.text(v, y, f" {v:.4f}", va="center", fontsize=8)
    fig.tight_layout(); fig.savefig(reports / "figs" / "comparison.png", dpi=150)

    write_error_figure(errors, reports)
    print("Done: comparison.csv/json, error_analysis.json, figs/comparison.png, figs/error_analysis.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
