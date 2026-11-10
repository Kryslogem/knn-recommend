"""ModelRegistry: giữ mô hình đang phục vụ trong RAM, hot-swap an toàn, đồng bộ phiên bản vào DB."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.models import ModelVersion
from ml.models.artifact import Bundle, load_artifact


class ModelRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bundle: Bundle | None = None
        self._stats: dict[int, tuple[float, int]] = {}
        self.loaded_at: datetime | None = None

    def get(self) -> Bundle | None:
        return self._bundle  # đọc tham chiếu là nguyên tử; hot-swap thay cả tham chiếu

    def swap(self, bundle: Bundle) -> None:
        """Thay mô hình đang phục vụ. Bundle đã nạp và kiểm tra xong trước khi gọi → không có lúc thiếu mô hình."""
        rm = bundle.knn.rm
        counts = rm.M.sum(axis=0)
        means = np.divide(rm.R.sum(axis=0), counts, out=np.zeros(rm.shape[1]), where=counts > 0)
        stats = {int(m): (float(a), int(c)) for m, a, c in zip(rm.item_ids, means, counts)}
        with self._lock:
            self._bundle, self._stats, self.loaded_at = bundle, stats, datetime.now(timezone.utc).replace(tzinfo=None)

    def movie_stats(self, movie_id: int) -> tuple[float | None, int]:
        """(điểm TB, số rating) tính từ TRAIN của mô hình đang chạy; (None, 0) nếu phim không có trong train."""
        a, c = self._stats.get(movie_id, (None, 0))
        return (round(a, 3) if c else None), c


def _rel(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def register_bundle(db: Session, bundle: Bundle, base: Path) -> ModelVersion:
    """Thêm phiên bản vào DB nếu chưa có (idempotent)."""
    row = db.scalar(select(ModelVersion).where(ModelVersion.version == bundle.version))
    if row:
        return row
    row = ModelVersion(
        version=bundle.version,
        algorithm=bundle.meta["algorithm"],
        config={"params": bundle.meta["params"], "serving": bundle.meta["serving"]},
        data_hash=bundle.meta.get("data_hash"),
        split_hash=bundle.meta.get("split_hash"),
        artifact_path=_rel(bundle.path, base),
        metrics_val=bundle.metrics.get("validation"),
        metrics_test=bundle.metrics.get("test"),
        includes_app_ratings=bool(bundle.meta.get("includes_app_ratings")),
    )
    db.add(row)
    db.commit()
    return row


def sync_artifacts(db: Session, models_dir: Path, base: Path) -> int:
    """Đăng ký mọi thư mục artifact chưa có trong DB (vd. mô hình huấn luyện bằng CLI). Trả số phiên bản mới."""
    n = 0
    if not models_dir.exists():
        return 0
    known = set(db.scalars(select(ModelVersion.version)))
    for d in sorted(p for p in models_dir.iterdir() if (p / "meta.json").exists()):
        try:
            version = json.loads((d / "meta.json").read_text(encoding="utf-8"))["version"]
            if version not in known:
                register_bundle(db, load_artifact(d), base)
                n += 1
        except Exception:  # artifact hỏng không được làm sập khởi động
            continue
    return n


def set_active(db: Session, row: ModelVersion) -> None:
    """Đúng MỘT phiên bản is_active, đổi trong một transaction."""
    db.execute(update(ModelVersion).values(is_active=False))
    row.is_active = True
    db.commit()
