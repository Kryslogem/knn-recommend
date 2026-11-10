"""Kiểm tra nhanh trên dữ liệu thật: fit trên TRAIN, báo RMSE/MAE trên VALIDATION.

Đây KHÔNG phải đánh giá chính thức (giai đoạn 3) và không đụng tới test.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402

from ml.data.split import load_split  # noqa: E402
from ml.models.baseline import BiasOnlyModel  # noqa: E402
from ml.models.knn import KNNModel  # noqa: E402
from ml.models.popular import PopularModel  # noqa: E402

s = load_split(ROOT / "data" / "processed")
train, val = s["train"], s["validation"]
models = [
    PopularModel(),
    BiasOnlyModel(),
    KNNModel("basic", k=40, shrinkage=0),
    KNNModel("baseline", k=40, shrinkage=0),
    KNNModel("baseline", k=40, shrinkage=100),
]
print(f"{'model':<28}{'fit(s)':>8}{'pred(s)':>9}{'RMSE':>8}{'MAE':>8}{'knn%':>7}")
for m in models:
    t = time.time(); m.fit(train); tf = time.time() - t
    t = time.time(); out = m.predict_frame(val); tp = time.time() - t
    err = out["est"].to_numpy() - val["rating"].to_numpy()
    label = m.name + (f"(shr={getattr(m, 'shrinkage', '')})" if hasattr(m, "shrinkage") else "")
    print(f"{label:<28}{tf:>8.2f}{tp:>9.2f}{np.sqrt((err**2).mean()):>8.4f}{np.abs(err).mean():>8.4f}{(out['source'] == 'knn').mean() * 100:>7.1f}")
