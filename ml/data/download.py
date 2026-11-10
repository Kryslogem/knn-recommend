"""Tải MovieLens 100K từ GroupLens, kiểm tra checksum và giải nén an toàn."""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path) -> Path:
    """Tải `url` về `dest` (bỏ qua nếu đã có)."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:  # dùng kho chứng chỉ hệ điều hành (Windows) nếu có; vẫn xác minh SSL
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass
    tmp =dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "knn-recommend-data-prep"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out)
    tmp.replace(dest)
    return dest


def safe_extract(zip_path: Path, dest_dir: Path) -> None:
    """Giải nén, từ chối mọi entry trỏ ra ngoài `dest_dir` (zip-slip)."""
    dest_root = dest_dir.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (dest_root / member.filename).resolve()
            if dest_root != target and dest_root not in target.parents:
                raise ValueError(f"Unsafe entry in zip: {member.filename}")
        zf.extractall(dest_root)


def fetch_movielens(url: str, raw_dir: str | Path, expected_sha256: str | None = None) -> dict:
    """Tải + kiểm tra + giải nén. Trả về thông tin nguồn để ghi vào báo cáo.

    Raises:
        ValueError: nếu checksum không khớp với giá trị cấu hình.
    """
    raw_dir = Path(raw_dir)
    zip_path = download_file(url, raw_dir / Path(url).name)
    digest = sha256_file(zip_path)
    if expected_sha256 and digest != expected_sha256.lower():
        raise ValueError(
            f"SHA-256 mismatch for {zip_path.name}: got {digest}, config says {expected_sha256}"
        )
    extracted = raw_dir / "ml-100k"
    if not (extracted / "u.data").exists():
        safe_extract(zip_path, raw_dir)
    return {
        "url": url,
        "zip_path": zip_path.as_posix(),
        "zip_sha256": digest,
        "checksum_verified": bool(expected_sha256),
        "extracted_dir": extracted.as_posix(),
    }
