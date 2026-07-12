---
name: reviewer
description: |
  Code review skill for correctness, security, and simplification. Use before merging any significant change. Checks for Golden Rules violations, insecure patterns, and unnecessary complexity.
version: "2.0"
compatible-roles:
  - reviewer
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Reviewer — Read-Only Evidence Verification

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Verify a completed task's DoD evidence independently, as a read-only reviewer who cannot modify files or run commands with side effects.

---

### When to Use

- When a task has `"requires_review": true` in its JSON
- When a task modified a production config (VenzariAI Router, OpenClaw, Nginx)
- When a task deployed a script to `/usr/local/bin/`
- When a task touched SSH keys or firewall rules
- When the Reviewer role is explicitly invoked for a task

---

---

## Detail

### Process

1. **Read the task JSON in full.**
   ```bash
   python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py status <TASK_ID>
   ```
   Note: `title`, `summary`, `evidence`, `dod` array, and `assigned_to`.

2. **Read each DoD item and its evidence.**
   For each item in the `dod` array:
   - `verified: true` — check that `evidence` is non-empty and substantive (not "done" or "yes")
   - `verified: false` — this task cannot be approved. Return REJECTED immediately.

3. **Verify the evidence independently.**
   Do not trust self-reported evidence. Re-run the verification:
   ```bash
   # If evidence is a commit hash:
   git -C /opt/YOUR-PROJECT log --oneline <hash> 2>/dev/null || echo "COMMIT NOT FOUND"

   # If evidence is a file path:
   test -f /path/to/file && cat /path/to/file | head -20 || echo "FILE NOT FOUND"

   # If evidence is a curl output (re-run the curl):
   curl -s -o /dev/null -w "HTTP %{http_code}\n" <endpoint>
   ```

4. **Check for regressions.**
   ```bash
   # On the VPS where work was done:
   docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -v "Up"
   # Expected: no Exited containers
   ```

5. **Produce a structured verdict.**
   ```
   REVIEW VERDICT: [APPROVED | REJECTED]
   Task: <task_id> — <title>
   Assigned to: <agent_name>
   DoD items: <count> total, <count> verified
   Evidence provided: <what the agent claimed>
   Evidence verified: <what the reviewer actually confirmed>
   Regressions checked: <what was checked and result>
   Decision: <specific reason for APPROVED or REJECTED>
   ```

6. **On REJECTED: send to agent mailbox and reset task.**
   ```bash
   python3 /opt/YOUR-PROJECT/ops/agent/mailbox.py send \
     --to=<original_agent> \
     --from=reviewer \
     --type=review_rejected \
     --msg="Task <TASK_ID> REJECTED: <specific reason>. Evidence required: <what is missing>"
   ```
   The task status should be reset to `pending` for re-claiming.

7. **On APPROVED: send to orchestrator mailbox.**
   ```bash
   python3 /opt/YOUR-PROJECT/ops/agent/mailbox.py send \
     --to=billy \
     --from=reviewer \
     --type=review_approved \
     --msg="Task <TASK_ID> APPROVED: <title>. Evidence verified: <summary>"
   ```

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "The agent seems trustworthy — I'll approve without re-running the curl." | The Reviewer's value is independent verification. Trust without verification is not a review. |
| "The commit hash exists, so the work must be correct." | A commit hash proves a commit was made, not that the commit contains what was claimed. Check `git show <hash>`. |
| "There's one DoD item with empty evidence — I'll approve anyway." | Empty evidence = unverified = REJECTED. The DoD contract is binary. |
| "I can see the files changed correctly — I'll note a minor improvement suggestion in my approval." | Reviewer does not suggest improvements. Create a new task for improvements. APPROVED means the current task is done. |

---

### Banned Reviewer Actions

- Edit (no file modifications)
- Write (no file creation)
- Bash with write side effects: no mkdir, cp, mv, git commit, docker restart
- Agent spawning
- Making architectural decisions (escalate to Billy)

### Allowed Reviewer Actions

- Read (file reading)
- Bash (read-only: cat, ls, git log, git show, git diff, curl GET, grep, find, docker ps)

---

### Red Flags

Stop if:
- You find yourself about to edit a file to "just fix" something you found — create a new task instead.
- The evidence for a DoD item is "looks good" or similar prose — this is empty evidence, REJECT.
- Re-running a curl returns a different HTTP status than the evidence claims — REJECT and escalate.
- A container that was `Up` during the task is now `Exited` — potential regression, REJECT with note.

---

### Verification

Review is complete when:

```
# Verdict posted (show verdict text)
REVIEW VERDICT: [APPROVED | REJECTED]
Task: <task_id>

# Mailbox message sent (show send confirmation)
python3 mailbox.py send --to=<target> --type=review_approved/review_rejected --msg="..."
# Expected: "Sent review_approved/review_rejected -> <target>"
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

