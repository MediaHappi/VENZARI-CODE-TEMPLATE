#!/usr/bin/env python3
"""
ops/agent/drift_scanner.py
Checks for architecture drift between .venzari/project.yaml (SSOT)
and the actual state of the repository.

Usage:
  python3 ops/agent/drift_scanner.py
  python3 ops/agent/drift_scanner.py --strict  # exit 1 on drift
"""

import json
import os
import sys
import argparse
from pathlib import Path

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


REPO_ROOT = Path(__file__).parent.parent.parent
PROJECT_YAML = REPO_ROOT / ".venzari" / "project.yaml"
CURRENT_STATE = REPO_ROOT / "system-map" / "CURRENT_STATE.md"
CONTEXT_MD = REPO_ROOT / "CONTEXT.md"
GOLDEN_RULES = REPO_ROOT / "GOLDEN_RULES.md"
TASKS_DIR = REPO_ROOT / ".tasks"


def check(condition: bool, label: str, detail: str = "") -> dict:
    return {"label": label, "ok": condition, "detail": detail}


def run_checks() -> list[dict]:
    results = []

    # 1. project.yaml exists and is not a placeholder
    if PROJECT_YAML.exists():
        content = PROJECT_YAML.read_text(encoding="utf-8")
        has_placeholders = "[FILL IN" in content
        results.append(check(
            not has_placeholders,
            "project.yaml has no placeholders",
            "Fill in [FILL IN] sections in .venzari/project.yaml" if has_placeholders else ""
        ))
    else:
        results.append(check(False, "project.yaml exists", "Missing .venzari/project.yaml — run venzari-code install"))

    # 2. CURRENT_STATE.md exists and is not all placeholders
    if CURRENT_STATE.exists():
        content = CURRENT_STATE.read_text(encoding="utf-8")
        placeholder_lines = content.count("[FILL IN")
        results.append(check(
            placeholder_lines < 5,
            "CURRENT_STATE.md is populated",
            f"{placeholder_lines} [FILL IN] sections remaining" if placeholder_lines >= 5 else ""
        ))
    else:
        results.append(check(False, "system-map/CURRENT_STATE.md exists", "Missing system-map/CURRENT_STATE.md"))

    # 3. CONTEXT.md exists
    results.append(check(CONTEXT_MD.exists(), "CONTEXT.md exists", "" if CONTEXT_MD.exists() else "Missing CONTEXT.md"))

    # 4. GOLDEN_RULES.md exists
    results.append(check(GOLDEN_RULES.exists(), "GOLDEN_RULES.md exists", "" if GOLDEN_RULES.exists() else "Missing GOLDEN_RULES.md"))

    # 5. .tasks/ directory exists
    results.append(check(TASKS_DIR.exists(), ".tasks/ directory exists", "" if TASKS_DIR.exists() else "Missing .tasks/ — run venzari-code install"))

    # 6. No secrets in tracked files (basic check — looks for real secret patterns)
    # Patterns require context: sk- must be followed by many chars (OpenAI key), not --skill
    import re
    secret_patterns = [
        (r"sk-[A-Za-z0-9]{20,}", "OpenAI key"),
        (r"ghp_[A-Za-z0-9]{10,}", "GitHub PAT"),
        (r"AKIA[A-Z0-9]{16}", "AWS Access Key"),
        (r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY", "Private key"),
    ]
    secret_found = False
    secret_detail = ""
    for md_file in REPO_ROOT.glob("**/*.md"):
        if ".git" in str(md_file) or "node_modules" in str(md_file):
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            for pattern, label in secret_patterns:
                if re.search(pattern, text):
                    secret_found = True
                    secret_detail = f"Possible {label} in {md_file.relative_to(REPO_ROOT)}"
                    break
        except OSError:
            continue
        if secret_found:
            break
    results.append(check(not secret_found, "No secrets in markdown files", secret_detail))

    # 7. No legacy-system references (skip this file itself — it contains the patterns as checks)
    this_file = Path(__file__).resolve()
    legacy_found = False
    legacy_detail = ""
    legacy_terms = ["JEANNE-CTO", "jeannebrain", "158.220.105.107"]
    for f in REPO_ROOT.rglob("*"):
        if f.is_dir() or ".git" in str(f) or "node_modules" in str(f):
            continue
        if f.resolve() == this_file:
            continue  # skip self
        if f.suffix not in (".md", ".yaml", ".yml", ".json", ".sh", ".ts"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for term in legacy_terms:
                if term in text:
                    legacy_found = True
                    legacy_detail = f"Legacy reference ({term}) in {f.relative_to(REPO_ROOT)}"
                    break
        except OSError:
            continue
        if legacy_found:
            break
    results.append(check(not legacy_found, "No legacy-system references in repo", legacy_detail))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="VENZARI CODE drift scanner")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any drift found")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    args = parser.parse_args()

    results = run_checks()
    passed = sum(1 for r in results if r["ok"])
    failed = sum(1 for r in results if not r["ok"])

    if args.json_output:
        print(json.dumps({"results": results, "passed": passed, "failed": failed}, indent=2))
    else:
        print(f"\nVENZARI CODE Drift Scanner — {REPO_ROOT.name}\n")
        for r in results:
            icon = "✅" if r["ok"] else "❌"
            line = f"  {icon}  {r['label']}"
            if not r["ok"] and r.get("detail"):
                line += f"\n       → {r['detail']}"
            print(line)
        print(f"\n{passed} passed, {failed} failed\n")

    if args.strict and failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
