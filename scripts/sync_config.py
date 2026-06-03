#!/usr/bin/env python3
"""Sync .env from models.yaml and validate LM Studio model IDs."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]


def load_models_yaml() -> dict:
    path = ROOT / "config" / "models.yaml"
    if yaml is None:
        raise RuntimeError("pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def check_lm_studio(url: str, expected: list[str]) -> None:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/v1/models", timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"WARN: LM Studio unreachable at {url}: {exc}")
        return
    ids = [m.get("id") for m in data.get("data", [])]
    for model_id in expected:
        if model_id in ids:
            print(f"OK model loaded: {model_id}")
        else:
            print(f"WARN model not in /v1/models: {model_id}")


def main() -> int:
    cfg = load_models_yaml()
    llm = cfg["models"]["llm"]["id"]
    embed = cfg["models"]["embedding"]["id"]
    env_path = ROOT / ".env"
    example = ROOT / ".env.example"
    if not env_path.exists() and example.exists():
        env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Created {env_path} from .env.example")
    upstream = os.getenv("LMSTUDIO_UPSTREAM", "http://127.0.0.1:1234")
    check_lm_studio(upstream, [llm, embed])
    print("sync_config complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
