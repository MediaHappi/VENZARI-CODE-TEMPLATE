#!/bin/bash
# Usage: bash /opt/YOUR-PROJECT/ops/agent/list-tasks.sh [status]
# Lists tasks, optionally filtered by status: pending|in_progress|completed
# With no argument, shows all tasks.
STATUS="${1:-all}"
cd /opt/YOUR-PROJECT

if [ "$STATUS" = "all" ]; then
    python3 ops/agent/task_manager.py list 2>/dev/null || true
else
    python3 -c "
import json, glob, sys
tasks = []
for f in sorted(glob.glob('/opt/YOUR-PROJECT/.tasks/*.json')):
    try:
        with open(f) as fh:
            d = json.load(fh)
        tasks.append(d)
    except Exception:
        pass
status_filter = sys.argv[1]
if status_filter != 'all':
    tasks = [t for t in tasks if t.get('status') == status_filter]
if not tasks:
    print('No tasks found')
    sys.exit(0)
print(f\"{'ID':<6} {'STATUS':<12} {'ASSIGNED':<20} {'TITLE'}\")
print('-' * 70)
for t in tasks:
    assigned = t.get('assigned_to') or '-'
    print(f\"{t['id']:<6} {t['status']:<12} {assigned:<20} {t['title']}\")
" "$STATUS"
fi
