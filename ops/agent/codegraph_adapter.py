#!/usr/bin/env python3
"""
Adapter for codegraph — code intelligence for [YOUR-AI-NAME] agents.
Replaces DEPRECATED: ops/agent/code_index.py and code_query.py

codegraph runs LOCALLY on Venzari VPS (consolidated single-VPS).
Index: /opt/YOUR-PROJECT/.codegraph/codegraph.db (on Venzari VPS — this machine)
CLI:   /home/billy/.local/bin/codegraph

Usage:
  python3 codegraph_adapter.py context "<task>" — build task context (L4, used by inject_context.py)
  python3 codegraph_adapter.py search "<query>"  — symbol search
  python3 codegraph_adapter.py index "<path>"    — re-index a directory
  python3 codegraph_adapter.py verify            — check binary and index
"""
import subprocess, sys, os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False

CODEGRAPH_BIN = os.environ.get("CODEGRAPH_BIN", "/home/billy/.local/bin/codegraph")
PROJECT_CTO_PATH = os.environ.get("PROJECT_CTO_PATH", "/opt/YOUR-PROJECT")

def run_local(args: list) -> subprocess.CompletedProcess:
    """Run codegraph locally (no SSH — index is on this machine)."""
    return subprocess.run(
        [CODEGRAPH_BIN] + args,
        capture_output=True, text=True,
        cwd=PROJECT_CTO_PATH
    )

def verify():
    """Check that codegraph binary exists and the local index is present."""
    if not os.path.isfile(CODEGRAPH_BIN):
        print(f"ERROR: codegraph binary not found at {CODEGRAPH_BIN}")
        print("Install: curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh")
        sys.exit(1)

    db_path = os.path.join(PROJECT_CTO_PATH, ".codegraph", "codegraph.db")
    if not os.path.isfile(db_path):
        print(f"ERROR: codegraph index not found at {db_path}")
        print(f"Build: cd {PROJECT_CTO_PATH} && codegraph init -i")
        sys.exit(1)

    result = run_local(["--version"])
    print(f"OK: codegraph {result.stdout.strip()} (local Venzari VPS)")
    print(f"OK: index at {db_path} ({os.path.getsize(db_path) // 1024} KB)")

def context(task: str):
    """Build L4 code intelligence context for a task — called by inject_context.py."""
    result = run_local(["context", task])
    if result.returncode != 0:
        # Non-fatal: empty L4 is acceptable
        sys.exit(0)
    print(result.stdout[:2000])  # cap at 2000 chars for token budget

def search(query: str):
    result = run_local(["query", query])
    if result.returncode != 0:
        print(f"ERROR: codegraph query failed:\n{result.stderr}")
        sys.exit(1)
    print(result.stdout)

def index(path: str):
    result = subprocess.run(
        [CODEGRAPH_BIN, "index"],
        capture_output=True, text=True,
        cwd=path
    )
    if result.returncode != 0:
        print(f"ERROR: codegraph index failed:\n{result.stderr}")
        sys.exit(1)
    print(result.stdout)

def main():
    if len(sys.argv) < 2:
        print("Usage: codegraph_adapter.py <search|index|verify> [arg]")
        print("  search <query>  — semantic search YOUR-PROJECT codebase (local)")
        print("  index <path>    — index a directory locally")
        print("  verify          — check codegraph binary and index are present")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "verify":
        verify()
    elif cmd == "context" and len(sys.argv) >= 3:
        context(sys.argv[2])
    elif cmd == "search" and len(sys.argv) >= 3:
        search(sys.argv[2])
    elif cmd == "index" and len(sys.argv) >= 3:
        index(sys.argv[2])
    else:
        print(f"Unknown command '{cmd}' or missing argument")
        sys.exit(1)

if __name__ == "__main__":
    main()
