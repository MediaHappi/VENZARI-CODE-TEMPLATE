#!/bin/bash
# run-task.sh — claim next task, create worktree, export environment
# Usage: eval $(bash /opt/YOUR-PROJECT/ops/agent/run-task.sh <AGENT_NAME>)
# Outputs: export TASK_ID TASK_TITLE TASK_LAYER TASK_WORKTREE PROJECT_CTO
# Exit 0 = task claimed, exit 1 = no tasks available

set -euo pipefail
AGENT="${1:?Usage: run-task.sh <AGENT_NAME>}"
REPO="/opt/YOUR-PROJECT"
cd "$REPO"

# Step 1: Claim next available task
claim_out=$(bash ops/agent/claim.sh "$AGENT" 2>/dev/null) || {
    echo "NO_TASKS" >&2; exit 1
}

# Expect: "CLAIMED 0001: task title here"
if ! echo "$claim_out" | grep -qE "^CLAIMED [0-9]+:"; then
    echo "CLAIM_ERROR: $claim_out" >&2; exit 1
fi

TASK_ID=$(echo "$claim_out" | grep -oE "^CLAIMED ([0-9]+):" | grep -oE "[0-9]+")
TASK_TITLE=$(echo "$claim_out" | sed 's/^CLAIMED [0-9]*: //')

# Step 2: Get task layer from JSON
task_file=$(ls ".tasks/${TASK_ID}-"*.json 2>/dev/null | head -1)
if [ -n "$task_file" ]; then
    TASK_LAYER=$(python3 -c "import json; print(json.load(open('$task_file')).get('layer','unknown'))" 2>/dev/null || echo "unknown")
else
    TASK_LAYER="unknown"
fi

# Step 3: Try to create a worktree for isolation
# worktree.py create prints "Created worktree: <path>" on success
TASK_WORKTREE="$REPO"
if python3 ops/agent/worktree.py create "$TASK_ID" > /tmp/.wt_out 2>&1; then
    wt=$(grep "^Created worktree:" /tmp/.wt_out | sed 's/^Created worktree: //' | head -1)
    [ -n "$wt" ] && TASK_WORKTREE="$wt"
fi

# Step 4: Send notification to orchestrator mailbox
python3 ops/agent/mailbox.py send \
    --to=orchestrator \
    --from="$AGENT" \
    --type=task_claimed \
    --msg="Agent $AGENT claimed task $TASK_ID: $TASK_TITLE [layer=$TASK_LAYER]" >/dev/null 2>&1 || true

# Output exports
cat <<EOF
export TASK_ID="$TASK_ID"
export TASK_TITLE="$TASK_TITLE"
export TASK_LAYER="$TASK_LAYER"
export TASK_WORKTREE="$TASK_WORKTREE"
export PROJECT_CTO="$REPO"
EOF
