#!/usr/bin/env bash
# ops/agent/claim.sh — Claim a task using venzari-code CLI or task_manager.py fallback
# Usage: ./ops/agent/claim.sh <task-id>

set -euo pipefail

TASK_ID="${1:-}"
if [[ -z "$TASK_ID" ]]; then
  echo "Usage: $0 <task-id>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Try venzari-code CLI first
if command -v venzari-code &>/dev/null; then
  venzari-code claim "$TASK_ID" --role implement
  exit 0
fi

# Fallback: use task_manager.py directly
cd "$REPO_ROOT"
python3 ops/agent/task_manager.py claim "$TASK_ID"
