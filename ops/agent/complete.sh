#!/bin/bash
# complete.sh — mark a task completed with evidence
# Usage: bash /opt/YOUR-PROJECT/ops/agent/complete.sh <TASK_ID> <SUMMARY> [EVIDENCE]
# EVIDENCE: commit hash, curl output, file path, test result — proves work was done
#
# DoD enforcement: if the task JSON has dod[] items, ALL must be verified=true with
# non-empty evidence before this script will proceed. This implements the completion
# contract from ABSORPTION_STRATEGY.md §3 (claude-code-harness pattern).
#
# To bypass DoD check (emergency only): SKIP_DOD=1 bash complete.sh <TASK_ID> ...
set -euo pipefail

TASK_ID="${1:?Usage: complete.sh <TASK_ID> <SUMMARY> [EVIDENCE]}"
SUMMARY="${2:?Summary required}"
EVIDENCE="${3:-}"
SKIP_DOD="${SKIP_DOD:-0}"

REPO="/opt/YOUR-PROJECT"
cd "$REPO"

# --- DoD Enforcement ---
# Read the task JSON and verify all dod items before proceeding
if [ "$SKIP_DOD" != "1" ]; then
    DOD_CHECK=$(python3 - <<PYEOF
import json, sys, glob

task_id = "$TASK_ID"
tasks_dir = "$REPO/.tasks"

# Find the task file
matches = glob.glob(f"{tasks_dir}/{task_id}*.json")
if not matches:
    print("ERROR:NOTFOUND")
    sys.exit(0)

with open(matches[0]) as f:
    task = json.load(f)

dod = task.get('dod', [])
if not dod:
    print("OK:NODOD")
    sys.exit(0)

failures = []
for item in dod:
    if not item.get('verified', False):
        failures.append(f"NOT VERIFIED: {item['item']}")
    elif not item.get('evidence', '').strip():
        failures.append(f"NO EVIDENCE: {item['item']}")

if failures:
    for f in failures:
        print(f"DOD_FAIL:{f}")
else:
    print(f"OK:{len(dod)} dod items verified")
PYEOF
    )

    # Check DoD result
    if echo "$DOD_CHECK" | grep -q "^DOD_FAIL:"; then
        echo "" >&2
        echo "ERROR: DoD check failed for task $TASK_ID. Cannot complete." >&2
        echo "Unverified or un-evidenced DoD items:" >&2
        echo "$DOD_CHECK" | grep "^DOD_FAIL:" | sed 's/^DOD_FAIL:/  - /' >&2
        echo "" >&2
        echo "Fix each DoD item, then call complete.sh again." >&2
        echo "To update a DoD item, edit the task JSON directly:" >&2
        echo "  /opt/YOUR-PROJECT/.tasks/${TASK_ID}*.json" >&2
        echo "  Set verified=true and evidence=<proof>" >&2
        echo "" >&2
        echo "To bypass (EMERGENCY ONLY): SKIP_DOD=1 bash complete.sh $TASK_ID \"$SUMMARY\" \"${EVIDENCE}\"" >&2
        exit 1
    elif echo "$DOD_CHECK" | grep -q "^ERROR:NOTFOUND"; then
        echo "ERROR: Task $TASK_ID not found in .tasks/" >&2
        exit 1
    fi
fi

# --- Evidence Warning ---
if [ -z "$EVIDENCE" ]; then
    echo "WARNING: completing task $TASK_ID without evidence. Provide commit hash or curl output." >&2
fi

# --- Complete the task ---
if [ -n "$EVIDENCE" ]; then
    python3 ops/agent/task_manager.py complete "$TASK_ID" "$SUMMARY" --evidence "$EVIDENCE"
else
    python3 ops/agent/task_manager.py complete "$TASK_ID" "$SUMMARY"
fi

echo "COMPLETED $TASK_ID"

# --- Write memory observation (best-effort, non-blocking) ---
# Records task completion to ChromaDB so future agents learn from this work.
(
    python3 ops/agent/memory_write.py write \
        --agent "${PROJECT_AGENT_NAME:-unknown}" \
        --type milestone \
        --summary "Task $TASK_ID completed: $SUMMARY" \
        --detail "Task: $TASK_ID | Evidence: ${EVIDENCE:-none provided} | Agent: ${PROJECT_AGENT_NAME:-unknown}" \
        --tags "task-$TASK_ID" "completed" \
        2>/dev/null
) &

exit 0
