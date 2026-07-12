#!/bin/bash
# approval-gate.sh — Billy approval queue manager.
#
# Agents write approval requests here when they need Billy's sign-off BEFORE proceeding.
# Required for: GOLDEN_RULES changes, architecture changes, new vendor imports, Plan X implementations.
#
# Usage:
#   approval-gate.sh list                    # show all pending approvals
#   approval-gate.sh list --all              # show all including approved/rejected
#   approval-gate.sh request "<title>" "<description>" <type>  # create approval request
#   approval-gate.sh approve <id>            # Billy approves
#   approval-gate.sh reject <id> "<reason>"  # Billy rejects
#   approval-gate.sh status <id>             # check one request
#
# Types: architecture | golden-rule | vendor-import | plan | security | other
#
# Schema: {"id": "APR-001", "type": "architecture", "title": "...", "description": "...",
#          "created_at": "ISO8601", "status": "pending|approved|rejected",
#          "github_issue_url": "", "approved_by": "", "approved_at": "", "reject_reason": ""}
#
# GitHub integration: --gh flag creates a GitHub issue with label 'needs-billy-approval'

set -uo pipefail

REPO="${PROJECT_CTO_PATH:-/opt/YOUR-PROJECT}"
INBOX="$REPO/.team/inbox/billy-approvals.jsonl"
touch "$INBOX"

ACTION="${1:-list}"

_next_id() {
  local max=0
  while IFS= read -r line; do
    local n
    n=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(int(d.get('id','APR-000').split('-')[1]))" 2>/dev/null || echo 0)
    [ "$n" -gt "$max" ] && max=$n
  done < "$INBOX"
  printf "APR-%03d" $((max + 1))
}

case "$ACTION" in
  list)
    SHOW_ALL="${2:-}"
    echo "=== Billy Approval Queue ==="
    FOUND=0
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      STATUS=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('status',''))" 2>/dev/null)
      [ "$SHOW_ALL" != "--all" ] && [ "$STATUS" != "pending" ] && continue
      FOUND=1
      echo "$line" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
icon = {'pending': '⏳', 'approved': '✅', 'rejected': '❌'}.get(d.get('status'), '?')
print(f\"{icon} [{d.get('id')}] {d.get('type','').upper()} — {d.get('title','')}\")
print(f\"   Created: {d.get('created_at','')[:10]}\")
print(f\"   {d.get('description','')[:120]}...\")
if d.get('github_issue_url'): print(f\"   Issue: {d.get('github_issue_url')}\")
if d.get('status') == 'approved': print(f\"   Approved by: {d.get('approved_by','')} at {d.get('approved_at','')[:10]}\")
if d.get('status') == 'rejected': print(f\"   Rejected: {d.get('reject_reason','')}\")
print()
" 2>/dev/null
    done < "$INBOX"
    [ "$FOUND" -eq 0 ] && echo "  No pending approvals."
    ;;

  request)
    TITLE="${2:-}"
    DESC="${3:-}"
    TYPE="${4:-other}"
    GH_FLAG="${5:-}"
    if [ -z "$TITLE" ]; then
      echo "Usage: approval-gate.sh request \"<title>\" \"<description>\" <type> [--gh]" >&2
      exit 1
    fi
    ID=$(_next_id)
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    ENTRY=$(python3 -c "
import json, sys
d = {
  'id': '$ID',
  'type': '$TYPE',
  'title': '''$TITLE''',
  'description': '''$DESC''',
  'created_at': '$TS',
  'status': 'pending',
  'github_issue_url': '',
  'approved_by': '',
  'approved_at': '',
  'reject_reason': ''
}
print(json.dumps(d))
")
    echo "$ENTRY" >> "$INBOX"
    echo "Created approval request: $ID"

    # Optionally create GitHub issue
    if [ "$GH_FLAG" = "--gh" ]; then
      if command -v gh &>/dev/null; then
        ISSUE_URL=$(gh issue create \
          --repo "MEDIA-HAPPI-AI/YOUR-PROJECT" \
          --title "[$TYPE] Needs Billy approval: $TITLE" \
          --label "needs-billy-approval" \
          --body "## Approval Request $ID

**Type:** $TYPE
**Created:** $TS

## Description

$DESC

## How to approve

Comment \`/approve\` on this issue, or run:
\`\`\`bash
bash /usr/local/bin/jeanne-approval-gate approve $ID
\`\`\`
" 2>/dev/null)
        if [ -n "$ISSUE_URL" ]; then
          # Update the entry with issue URL
          python3 << PYEOF
import json
lines = open('$INBOX').readlines()
updated = []
for line in lines:
    try:
        d = json.loads(line)
        if d.get('id') == '$ID':
            d['github_issue_url'] = '$ISSUE_URL'
        updated.append(json.dumps(d))
    except: updated.append(line.rstrip())
open('$INBOX', 'w').write('\n'.join(l for l in updated if l) + '\n')
PYEOF
          echo "GitHub issue: $ISSUE_URL"
        fi
      fi
    fi
    ;;

  approve)
    ID="${2:-}"
    [ -z "$ID" ] && echo "Usage: approval-gate.sh approve <APR-XXX>" >&2 && exit 1
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    python3 << PYEOF
import json
lines = open('$INBOX').readlines()
updated = []; found = False
for line in lines:
    try:
        d = json.loads(line)
        if d.get('id') == '$ID':
            d['status'] = 'approved'
            d['approved_by'] = 'billy'
            d['approved_at'] = '$TS'
            found = True
        updated.append(json.dumps(d))
    except: updated.append(line.rstrip())
open('$INBOX', 'w').write('\n'.join(l for l in updated if l) + '\n')
print('Approved: $ID' if found else 'ERROR: $ID not found')
PYEOF
    ;;

  reject)
    ID="${2:-}"; REASON="${3:-no reason given}"
    [ -z "$ID" ] && echo "Usage: approval-gate.sh reject <APR-XXX> \"<reason>\"" >&2 && exit 1
    python3 << PYEOF
import json
lines = open('$INBOX').readlines()
updated = []; found = False
for line in lines:
    try:
        d = json.loads(line)
        if d.get('id') == '$ID':
            d['status'] = 'rejected'; d['reject_reason'] = '$REASON'; found = True
        updated.append(json.dumps(d))
    except: updated.append(line.rstrip())
open('$INBOX', 'w').write('\n'.join(l for l in updated if l) + '\n')
print('Rejected: $ID' if found else 'ERROR: $ID not found')
PYEOF
    ;;

  status)
    ID="${2:-}"
    grep "\"id\": \"$ID\"" "$INBOX" 2>/dev/null | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
print(json.dumps(d, indent=2))
" 2>/dev/null || echo "Not found: $ID"
    ;;

  *)
    echo "Unknown action: $ACTION" >&2
    echo "Usage: approval-gate.sh list|request|approve|reject|status" >&2
    exit 1
    ;;
esac
