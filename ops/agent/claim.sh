#!/bin/bash
# Usage: bash /opt/YOUR-PROJECT/ops/agent/claim.sh <AGENT_NAME>
# Claims the next available task and prints its ID and title.
# Exit 0 = task claimed, Exit 1 = no tasks available
set -euo pipefail

AGENT="${1:?Usage: claim.sh <AGENT_NAME>}"
cd /opt/YOUR-PROJECT

result=$(python3 ops/agent/task_manager.py claim "$AGENT" 2>/dev/null)

if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status')=='in_progress' else 1)" 2>/dev/null; then
    id=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['id'])")
    title=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['title'])")
    echo "CLAIMED $id: $title"
    exit 0
else
    echo "NO_TASKS"
    exit 1
fi
