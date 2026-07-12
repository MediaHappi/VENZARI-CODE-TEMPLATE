#!/usr/bin/env python3
"""Validate advisor framework v2 files."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "ops/agent/advisor_protocol.py",
    "ops/agent/advisor_prompt_templates.py",
    "ops/agent/advisor_provider_adapters.py",
    "ops/agent/advisor_orchestrator.py",
    "docs/governance/ADVISOR-SYSTEM.md",
]


def validate() -> list[str]:
    failures = []
    for rel in REQUIRED:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing {rel}")
        elif "TODO" in path.read_text(errors="ignore"):
            failures.append(f"{rel} contains TODO")
    templates = ROOT / "ops/agent/advisor_prompt_templates.py"
    text = templates.read_text(errors="ignore") if templates.exists() else ""
    for name in ("task_review", "historical_verification", "repo_map", "closing_gate", "documentation", "security"):
        if name not in text:
            failures.append(f"missing advisor template {name}")
    if "Do not suggest swarms" not in text:
        failures.append("advisor prompt templates missing no-swarm concurrency rule")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("ADVISOR FRAMEWORK GUARD FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("ADVISOR FRAMEWORK GUARD PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
