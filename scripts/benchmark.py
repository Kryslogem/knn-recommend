"""NFR01 benchmark: end-to-end latency of the recommendation endpoint over real HTTP.

    python scripts/benchmark.py [--url http://127.0.0.1:8000] [--n 300]

Use 127.0.0.1, not localhost: on Windows, urllib tries IPv6 (::1) first and waits ~2 s before falling back to
IPv4, which would add a fake 2-second delay to every request (a client artifact, not a server cost).

Requires a running backend with a seeded database and an active model. Measures
GET /admin/recommendations/movielens/{id}, which is NOT cached and runs the same fold-in path
as a web user (DB read of the profile, similarity to all 943 training users, Top-10, JSON).
Writes docs/benchmark.md including the machine configuration, as NFR01 requires.
"""

import argparse
import ctypes
import json
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402

from backend.app.config import get_settings  # noqa: E402


def machine_info() -> dict:
    info = {"os": platform.platform(), "python": platform.python_version(), "numpy": np.__version__, "logical_cpus": __import__("os").cpu_count()}
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor | Select-Object -First 1).Name"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
        info["cpu"] = out or platform.processor()
    except Exception:  # noqa: BLE001
        info["cpu"] = platform.processor()

    class MemStatus(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]

    try:
        m = MemStatus()
        m.dwLength = ctypes.sizeof(MemStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        info["ram_gb"] = round(m.ullTotalPhys / 1024**3, 1)
    except Exception:  # noqa: BLE001
        info["ram_gb"] = None
    return info


def call(url, path, token=None, method="GET", body=None):
    req = urllib.request.Request(url + "/api/v1" + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--n", type=int, default=300, help="number of distinct MovieLens profiles to request")
    args = ap.parse_args()

    s = get_settings()
    token = call(args.url, "/auth/login", method="POST", body={"username": s.seed_admin_username, "password": s.seed_admin_password})["access_token"]
    health = call(args.url, "/health")
    if not health["model_loaded"]:
        print("No model is active on the server.", file=sys.stderr)
        return 1

    for uid in range(1, 6):  # warm-up (first requests touch cold caches)
        call(args.url, f"/admin/recommendations/movielens/{uid}?n=10", token)

    lat, server_ms, sizes = [], [], []
    rng = np.random.default_rng(0)
    ids = rng.choice(np.arange(1, 944), size=min(args.n, 943), replace=False)
    for uid in ids:
        t = time.perf_counter()
        r = call(args.url, f"/admin/recommendations/movielens/{int(uid)}?n=10", token)
        lat.append((time.perf_counter() - t) * 1000)
        server_ms.append(r["latency_ms"])
        sizes.append(r["profile_size"])

    pct = lambda a, q: float(np.percentile(a, q))  # noqa: E731
    res = {
        "requests": len(lat),
        "end_to_end_ms": {"p50": pct(lat, 50), "p95": pct(lat, 95), "p99": pct(lat, 99), "max": max(lat)},
        "fold_in_only_ms": {"p50": pct(server_ms, 50), "p95": pct(server_ms, 95), "max": max(server_ms)},
        "profile_size": {"min": int(min(sizes)), "median": float(np.median(sizes)), "max": int(max(sizes))},
    }
    target_ms = 2000
    ok = res["end_to_end_ms"]["p95"] < target_ms
    mi = machine_info()
    e, f, p = res["end_to_end_ms"], res["fold_in_only_ms"], res["profile_size"]
    md = f"""# NFR01 benchmark: Top-10 recommendation latency

Target (NFR01): Top-10 in about 2 seconds once the model is loaded. **Result: {'MET' if ok else 'NOT MET'}** (p95 = {e['p95']:.1f} ms).

## Method
- Endpoint: `GET /admin/recommendations/movielens/{{id}}?n=10` over real HTTP to `{args.url}` (uncached; same fold-in path as a web user).
- {res['requests']} distinct MovieLens profiles drawn at random (seed 0), after 5 warm-up requests; profiles had {p['min']} to {p['max']} rated films (median {p['median']:.0f}).
- Active model: `{health['model_version']}`.
- Client and server ran on the same machine, so network latency is negligible. Includes DB read, fold-in against all 943 training users, Top-10, enrichment and JSON.

## Results (milliseconds)
| Measure | p50 | p95 | max |
|---|---:|---:|---:|
| End-to-end (client-timed) | {e['p50']:.1f} | {e['p95']:.1f} | {e['max']:.1f} |
| Fold-in + ranking only (server-reported) | {f['p50']:.1f} | {f['p95']:.1f} | {f['max']:.1f} |

p99 end-to-end: {e['p99']:.1f} ms.

## Machine
| Item | Value |
|---|---|
| OS | {mi['os']} |
| CPU | {mi['cpu']} ({mi['logical_cpus']} logical CPUs) |
| RAM | {mi['ram_gb']} GB |
| Python / NumPy | {mi['python']} / {mi['numpy']} |

Generated by `scripts/benchmark.py`. Re-run it on the demo machine and report that machine's numbers.
"""
    (ROOT / "docs" / "benchmark.md").write_text(md, encoding="utf-8")
    (ROOT / "docs" / "benchmark.json").write_text(json.dumps({"result": res, "machine": mi, "model": health["model_version"]}, indent=2), encoding="utf-8")
    print(md)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
