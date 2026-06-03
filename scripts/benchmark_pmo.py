#!/usr/bin/env python3
"""Empirical PMO KPI benchmark harness."""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)


def post(url: str, token: str, body: dict | None = None) -> tuple[float, dict]:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "X-PMO-Token": token},
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as resp:
        payload = json.loads(resp.read().decode())
    elapsed = time.perf_counter() - start
    return elapsed, payload


def main() -> int:
    token = "change-me-pmo-secret-2026"
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("WEBHOOK_SECRET="):
                token = line.split("=", 1)[1].strip()

    rows = []
    base = "http://localhost:8080/api/pmo"

    for name, path, body in [
        ("ingest", f"{base}/ingest", {}),
        ("letter", f"{base}/letter", {"contractor_name": "الف", "delay_subject": "فاز ۳"}),
        ("risk", f"{base}/risk/run", {}),
        ("chat", f"{base}/chat", {"prompt": "سلام کوتاه", "use_rag": False}),
    ]:
        try:
            elapsed, payload = post(path, token, body)
            rows.append(
                {
                    "scenario": name,
                    "seconds": round(elapsed, 2),
                    "status": payload.get("status", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            rows.append(
                {
                    "scenario": name,
                    "seconds": -1,
                    "status": f"error: {exc}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    csv_path = DOCS / "benchmark_raw.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["scenario", "seconds", "status", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)

    md_path = DOCS / "benchmark_results.md"
    md_path.write_text(
        "# PMO Benchmark Results\n\n"
        f"Generated: {datetime.now().isoformat()}\n\n"
        "| Scenario | Seconds | Status |\n|---|---|---|\n"
        + "\n".join(f"| {r['scenario']} | {r['seconds']} | {r['status']} |" for r in rows)
        + "\n\nNote: Replace KPI claims in article with measured values only.\n",
        encoding="utf-8",
    )
    print(f"Wrote {csv_path} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
