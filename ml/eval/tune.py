"""Grid search siêu tham số trên VALIDATION (không đụng test).

Tối ưu: fit chỉ khi đổi (reg_u, reg_i, n_epochs, shrinkage, min_support); k và min_k đổi trên mô hình đã fit.
Tiêu chí chọn: RMSE validation (làm tròn 4 chữ số) thấp nhất; hòa thì NDCG@10 cao hơn.
NDCG chỉ tính cho `ndcg_top` cấu hình có RMSE tốt nhất vì tính xếp hạng toàn danh mục khá tốn thời gian.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from ml.eval.evaluate import _items_by_user, allowed_mask, evaluate_model, rank_from_scores, ranking_block, relevant_items
from ml.eval.metrics import rmse
from ml.models.knn import KNNModel


def run_grid(train: pd.DataFrame, val: pd.DataFrame, grid: dict, log=print) -> pd.DataFrame:
    rows = []
    fits = list(itertools.product(grid["reg"], grid["n_epochs"], grid["shrinkage"], grid["min_support"]))
    for n, ((reg_u, reg_i), n_epochs, shrinkage, min_support) in enumerate(fits, 1):
        model = KNNModel(
            "baseline", k=grid["k"][0], min_k=1, shrinkage=shrinkage, min_support=min_support,
            n_epochs=n_epochs, reg_u=reg_u, reg_i=reg_i,
        ).fit(train)
        for min_k, k in itertools.product(grid["min_k"], grid["k"]):
            model.k, model.min_k = k, min_k
            out = model.predict_frame(val)
            rows.append(
                {
                    "reg_u": reg_u, "reg_i": reg_i, "n_epochs": n_epochs, "shrinkage": shrinkage,
                    "min_support": min_support, "min_k": min_k, "k": k,
                    "val_rmse": rmse(val["rating"], out["est"]),
                    "val_mae": float((out["est"] - val["rating"]).abs().mean()),
                    "val_knn_coverage": float((out["source"] == "knn").mean()),
                }
            )
        log(f"  fit {n}/{len(fits)} xong")
    return pd.DataFrame(rows)


def select_best(results: pd.DataFrame, train, val, catalog_ids, ndcg_top: int = 3, log=print) -> tuple[dict, pd.DataFrame]:
    """Chọn cấu hình tốt nhất; thêm cột val_ndcg@10 cho ndcg_top ứng viên đứng đầu."""
    results = results.sort_values("val_rmse").reset_index(drop=True)
    results["val_ndcg@10"] = float("nan")
    for i in range(ndcg_top):
        r = results.loc[i]
        model = KNNModel(
            "baseline", k=int(r.k), min_k=int(r.min_k), shrinkage=r.shrinkage, min_support=int(r.min_support),
            n_epochs=int(r.n_epochs), reg_u=r.reg_u, reg_i=r.reg_i,
        ).fit(train)
        m, _ = evaluate_model(model, val, train, catalog_ids)
        results.loc[i, "val_ndcg@10"] = m["ndcg@10"]
        log(f"  top{i + 1}: rmse={r.val_rmse:.4f} ndcg@10={m['ndcg@10']:.4f}")
    top = results.head(ndcg_top).copy()
    top["rmse_r4"] = top["val_rmse"].round(4)
    best = top.sort_values(["rmse_r4", "val_ndcg@10"], ascending=[True, False]).iloc[0]
    keys = ["reg_u", "reg_i", "n_epochs", "shrinkage", "min_support", "min_k", "k"]
    cfg = {key: (float(best[key]) if key in ("reg_u", "reg_i", "shrinkage") else int(best[key])) for key in keys}
    return cfg, results


def choose_item_threshold(
    model, val, train, catalog_ids, grid: list[int], k: int = 10, min_candidate_share: float = 0.25, log=print
) -> tuple[int, pd.DataFrame]:
    """Chọn ngưỡng số rating tối thiểu của phim khi xếp hạng, theo NDCG@10 trên VALIDATION,
    với ràng buộc giữ >= `min_candidate_share` danh mục làm ứng viên.

    `model` đã fit trên train. Điểm chỉ tính một lần; hòa → ngưỡng nhỏ hơn.
    """
    catalog_ids = np.asarray(catalog_ids)
    relevant = relevant_items(val)
    users = sorted(relevant)
    exclude = _items_by_user(train)
    est, _ = model.score_matrix(users, catalog_ids)
    counts = train.groupby("movie_id").size()
    rows = []
    for t in sorted(grid):
        tops = rank_from_scores(est, users, catalog_ids, exclude, k, allowed_mask(catalog_ids, counts, t))
        m = ranking_block(tops, relevant, len(catalog_ids), k)
        n_ok = int(allowed_mask(catalog_ids, counts, t).sum())
        rows.append({"min_item_ratings": t, "n_candidate_items": n_ok, **{f"val_{a}": b for a, b in m.items()}})
        log(f"  threshold {t:>3}: {n_ok:>4} eligible films, NDCG@10={m[f'ndcg@{k}']:.4f}, Recall@10={m[f'recall@{k}']:.4f}")
    table = pd.DataFrame(rows)
    table["share_of_catalog"] = table["n_candidate_items"] / len(catalog_ids)
    # NDCG tăng đơn điệu theo ngưỡng nên chọn thuần NDCG sẽ thu danh sách về vài trăm phim phổ biến nhất;
    # ràng buộc: giữ tối thiểu `min_candidate_share` danh mục làm ứng viên.
    ok = table[table["share_of_catalog"] >= min_candidate_share]
    best = ok.sort_values([f"val_ndcg@{k}", "min_item_ratings"], ascending=[False, True]).iloc[0]
    return int(best["min_item_ratings"]), table


def tune_k_for_competitor(mode: str, cfg: dict, train, val, k_grid: list[int], shrinkage: float) -> tuple[int, list[dict]]:
    """Chọn k cho mô hình đối chứng (KNNBasic / KNNBaseline không shrinkage); các yếu tố khác giữ như cấu hình chốt."""
    model = KNNModel(
        mode, k=k_grid[0], min_k=cfg["min_k"], shrinkage=shrinkage, min_support=cfg["min_support"],
        n_epochs=cfg["n_epochs"], reg_u=cfg["reg_u"], reg_i=cfg["reg_i"],
    ).fit(train)
    curve = []
    for k in k_grid:
        model.k = k
        curve.append({"k": k, "val_rmse": rmse(val["rating"], model.predict_frame(val)["est"])})
    best = min(curve, key=lambda r: (round(r["val_rmse"], 4), r["k"]))
    return best["k"], curve
