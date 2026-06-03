#!/usr/bin/env python3
"""Validate n8n workflow JSON exports."""

from __future__ import annotations

import json
import sys
from pathlib import Path

KNOWN_PREFIXES = (
    "n8n-nodes-base.",
    "@n8n/n8n-nodes-langchain.",
)


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    if not nodes:
        errors.append("no nodes")
    for node in nodes:
        ntype = node.get("type", "")
        if not any(ntype.startswith(p) for p in KNOWN_PREFIXES):
            errors.append(f"unknown type: {ntype} in {node.get('name')}")
    if not data.get("connections"):
        errors.append("missing connections")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_workflow.py <file-or-dir>")
        return 1
    target = Path(sys.argv[1])
    files = [target] if target.is_file() else list(target.glob("*.json"))
    failed = False
    for wf in files:
        errs = validate(wf)
        if errs:
            failed = True
            print(f"FAIL {wf}: {', '.join(errs)}")
        else:
            print(f"PASS {wf}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
