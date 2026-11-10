"""Vẽ biểu đồ EDA cho báo cáo từ data/processed (chỉ dùng TRAIN để tránh rò rỉ thống kê)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ml.data.split import load_split  # noqa: E402

out = ROOT / "artifacts" / "reports" / "eda"
out.mkdir(parents=True, exist_ok=True)
train = load_split(ROOT / "data" / "processed")["train"]

fig, ax = plt.subplots(1, 3, figsize=(15, 4))
dist = train["rating"].value_counts().sort_index()
ax[0].bar(dist.index, dist.values, color="#4f46e5")
ax[0].set(title="Phân bố rating (train)", xlabel="Rating", ylabel="Số lượt")

per_user = train.groupby("user_id").size()
ax[1].hist(per_user, bins=40, color="#0891b2")
ax[1].set(title="Số rating mỗi người dùng (train)", xlabel="Số rating", ylabel="Số người dùng")

per_item = train.groupby("movie_id").size().sort_values(ascending=False).to_numpy()
ax[2].plot(range(1, len(per_item) + 1), per_item, color="#dc2626")
ax[2].set(title="Long-tail độ phổ biến phim (train)", xlabel="Hạng phim", ylabel="Số rating", yscale="log")

fig.tight_layout()
fig.savefig(out / "eda_overview.png", dpi=150)
print("Đã ghi", (out / "eda_overview.png").relative_to(ROOT).as_posix())
