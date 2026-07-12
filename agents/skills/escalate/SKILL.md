---
name: escalate
description: |
  Three-strike escalation protocol. Use when the same fix fails 3 times. Writes structured entry to .team/inbox/billy.jsonl and stops attempting the failing fix. Do NOT try a fourth time without human input.
version: "2.0"
compatible-roles:
  - infrastructure
  - backend
  - devops
  - discovery
  - data
  - frontend
  - memory
  - security
  - testing
  - reviewer
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Write
---

# Skill: Escalate — Three-Strike Protocol

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

When the same fix has failed three times, stop all work, send a structured escalation message to Billy's mailbox, and wait — do not attempt a fourth variation.

---

### When to Use

- After three consecutive failed attempts at the same task or fix (GOLDEN RULE 8)
- When a container will not stay up after three restarts
- When the same endpoint returns errors despite three different config changes
- When you are uncertain about a destructive action (deleting data, rotating keys, modifying firewall rules)
- When a security red flag is found (live key in git history, unknown open port)

---

---

## Detail

### Process

1. **Stop all work immediately.**
   Do not attempt fix #4. Do not try a "slightly different" approach. Stop.

2. **Document the three failures.**
   For each attempt, record:
   - What was changed
   - What was expected
   - What actually happened (show the error output)

3. **Increment failure_count in the task JSON.**
   ```bash
   python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py status <TASK_ID>
   # If failure_count is already 3, this task is in escalation
   ```
   The `failure_count` field is incremented automatically by `complete.sh` on failed evidence — but if you are stopping early, update it manually:
   ```python
   # In Python:
   import json
   from pathlib import Path
   path = next(Path('/opt/YOUR-PROJECT/.tasks').glob(f'{TASK_ID}*.json'))
   task = json.loads(path.read_text())
   task['failure_count'] = task.get('failure_count', 0) + 1
   path.write_text(json.dumps(task, indent=2))
   ```

4. **Write the escalation message to Billy's mailbox.**
   ```bash
   python3 /opt/YOUR-PROJECT/ops/agent/mailbox.py send \
     --to=billy \
     --from=<AGENT_NAME> \
     --type=escalation \
     --msg="ESCALATION — Task <TASK_ID>: <title>. Three failures:
   Attempt 1: <what was tried> → <what happened>
   Attempt 2: <what was tried> → <what happened>
   Attempt 3: <what was tried> → <what happened>
   Hypothesis: <what you think the root cause is>
   Next step needs: <what Billy needs to decide>"
   ```

5. **Set task status back to pending.**
   ```bash
   python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py complete <TASK_ID> "ESCALATED after 3 failures — awaiting Billy" --evidence "escalation sent to billy mailbox"
   ```
   Note: mark as completed with escalation note so the task does not block other tasks. Billy will re-open it.

6. **Write memory observation.**
   Use the memory-write skill to record all three attempts. Future agents must not repeat them.

7. **Stop. Do not pick up another task that touches the same service.**
   Picking up a related task while an escalation is pending risks compounding the failure.

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "Maybe a fourth attempt with a slightly different config will work." | Three identical failures signal a fundamental misunderstanding of the problem. A fourth attempt adds noise. Escalate. |
| "Billy is busy — I'll try one more thing." | Billy being busy does not change the three-strike rule. Unauthorized 4th attempts often cause harder-to-recover failures. |
| "The failures were different enough that they don't really count as 'three strikes.'" | If you are making this argument, you are rationalizing. Three attempts at fixing the same root issue = escalate. |
| "I'll escalate after I try the obvious fix I just thought of." | The obvious fix you just thought of is attempt 4. Escalate first, describe the fix in the escalation message. |

---

### Red Flags

The escalation skill itself should be used if:

- You find yourself writing this: "on the 4th attempt, I tried..." — you should have escalated at attempt 3.
- You are not sure if something qualifies as an "escalation." If you are unsure, it qualifies.
- A HITL-blocked action (from `hitl_wait.sh`) has timed out — treat timeout as rejection, escalate to Billy.

---

### Verification

Escalation is complete when:

```
# Mailbox message sent (show send confirmation)
python3 mailbox.py send --to=billy --type=escalation --msg="..."
# Expected: "Sent escalation -> billy"

# Task updated (show status)
python3 task_manager.py status <TASK_ID>
# Expected: failure_count >= 3, status="completed" (with escalation note)

# Memory written (confirm observation exists)
python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py query "<task title>"
# Expected: escalation observation appears
```

---

## Reference

### Forbidden Actions

| Action | Rule | Why |
|---|---|---|
| Skip SSOT commit | Rule 11 | Infrastructure must be in YOUR-PROJECT first |
| `docker restart` healthy container | Rule 1 | edit→rebuild→verify instead |
| `ANTHROPIC_BASE_URL` system-wide | Rule 13 | Breaks Claude Code OAuth |
| `liveTurnTimeoutMs` in openclaw.json | Rule 6 | Caused 2-day crash loop |

### Doc Impact

| Doc | What to update |
|---|---|
| `system-map/CURRENT_STATE.md` | Update service status if changed |

