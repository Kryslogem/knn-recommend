"""Giai đoạn 4: huấn luyện + lưu artifact có phiên bản.

    python scripts/train.py --config configs/model.yaml [--activate]
--activate ghi artifacts/models/active.json (backend giai đoạn 5 dùng làm mô hình khởi động).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from ml.data.load import load_yaml  # noqa: E402
from ml.pipeline import config_hash, run_training  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/model.yaml")
    ap.add_argument("--activate", action="store_true")
    args = ap.parse_args()

    cfg = load_yaml(ROOT / args.config)
    data_cfg = load_yaml(ROOT / "configs/data.yaml")
    processed = ROOT / data_cfg["paths"]["processed_dir"]
    reports = ROOT / data_cfg["paths"]["report_dir"]
    models_dir = ROOT / "artifacts" / "models"

    manifest = json.loads((processed / "split_manifest.json").read_text(encoding="utf-8"))
    if cfg.get("split_hash") != manifest["split_hash"]:
        print("model.yaml được chốt trên split khác — chạy lại scripts/tune.py.", file=sys.stderr)
        return 1

    # Gắn metrics test CHỈ nếu comparison.json là của đúng cấu hình này (không chạy lại test ở đây).
    test_metrics = None
    cmp_path = reports / "comparison.json"
    if cmp_path.exists():
        cmp = json.loads(cmp_path.read_text(encoding="utf-8"))
        if config_hash(cmp["config"]) == config_hash(cfg) and cmp["split_hash"] == manifest["split_hash"]:
            test_metrics = next(r for r in cmp["rows"] if r["model"] == "knn_baseline" and r["split"] == "test")

    res = run_training(cfg, processed, models_dir, test_metrics)
    print(f"Phiên bản: {res['version']}  ({res['path'].relative_to(ROOT).as_posix()})")
    v = res["metrics"]["validation"]
    print(f"  validation: RMSE={v['rmse']:.4f} NDCG@10(lọc)={v[f'ndcg@10_min{cfg['serving']['min_item_ratings']}']:.4f}")
    print("  metrics test:", "đã gắn từ lần đánh giá chính thức" if test_metrics else "chưa có (cấu hình chưa được evaluate.py chạy)")
    if args.activate:
        (models_dir / "active.json").write_text(json.dumps({"version": res["version"]}), encoding="utf-8")
        print("  đã kích hoạt: artifacts/models/active.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
