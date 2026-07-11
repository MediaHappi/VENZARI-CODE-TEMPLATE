#!/usr/bin/env bash
# ops/agent/complete.sh — Complete a task using venzari-code CLI or task_manager.py fallback
# Usage: ./ops/agent/complete.sh <task-id> "Summary of what was done" "Evidence: tests pass, etc"

set -euo pipefail

TASK_ID="${1:-}"
SUMMARY="${2:-}"
EVIDENCE="${3:-}"

if [[ -z "$TASK_ID" || -z "$SUMMARY" || -z "$EVIDENCE" ]]; then
  echo "Usage: $0 <task-id> <summary> <evidence>" >&2
  echo "  Example: $0 PROJ-001 'Added feature X' 'Tests: 42 pass. Typecheck clean.'" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Try venzari-code CLI first
if command -v venzari-code &>/dev/null; then
  venzari-code complete "$TASK_ID" \
    --summary "$SUMMARY" \
    --evidence "$EVIDENCE" \
    --skill implement
  exit 0
fi

# Fallback: use task_manager.py directly
cd "$REPO_ROOT"
python3 ops/agent/task_manager.py complete "$TASK_ID" \
  --summary "$SUMMARY" \
  --evidence "$EVIDENCE"
