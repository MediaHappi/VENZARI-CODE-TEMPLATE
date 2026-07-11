#!/usr/bin/env python3
"""
ops/agent/inject_context.py
Injects current CONTEXT.md and CURRENT_STATE.md into a running VENZARI CODE session.

Usage:
  python3 ops/agent/inject_context.py
  python3 ops/agent/inject_context.py --dry-run   # print what would be injected
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent
CONTEXT_MD = REPO_ROOT / "CONTEXT.md"
CURRENT_STATE_MD = REPO_ROOT / "system-map" / "CURRENT_STATE.md"


def read_file_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        return f"[Could not read {path.name}: {e}]"


def inject_via_cli(content: str, dry_run: bool) -> bool:
    """Try to inject via venzari-code CLI."""
    if not _venzari_available():
        return False
    if dry_run:
        print("[DRY RUN] Would call: venzari-code context inject --content <...>")
        return True
    try:
        result = subprocess.run(
            ["venzari-code", "context", "inject", "--content", content],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"venzari-code context inject failed: {e.stderr.strip()}", file=sys.stderr)
        return False


def _venzari_available() -> bool:
    try:
        subprocess.run(["venzari-code", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject VENZARI CODE context")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be injected without doing it")
    parser.add_argument("--context-only", action="store_true", help="Inject CONTEXT.md only")
    parser.add_argument("--state-only", action="store_true", help="Inject CURRENT_STATE.md only")
    args = parser.parse_args()

    parts: list[str] = []

    if not args.state_only:
        context = read_file_safe(CONTEXT_MD)
        parts.append(f"## CONTEXT.md\n\n{context}")

    if not args.context_only:
        state = read_file_safe(CURRENT_STATE_MD)
        parts.append(f"## system-map/CURRENT_STATE.md\n\n{state}")

    combined = "\n\n---\n\n".join(parts)

    if args.dry_run:
        print("=== Context that would be injected ===")
        print(combined[:2000])
        if len(combined) > 2000:
            print(f"\n... [{len(combined) - 2000} more chars] ...")
        return

    # Try CLI injection
    if inject_via_cli(combined, dry_run=args.dry_run):
        return

    # Fallback: print to stdout (pipe into session stdin)
    print("# VENZARI CODE Context Injection")
    print(combined)
    print("\n# [End of injected context]")


if __name__ == "__main__":
    main()
