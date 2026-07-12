---
doc_type: runbook
last_updated: 2026-07-06
ssot_status: CURRENT
audience: all-agents
---

# Session Boot Sequence — [YOUR-AI-NAME] V8
**For:** Every Claude session starting on Venzari VPS
**Time to operational:** < 2 minutes

---

## 0. 🔴 START SESSION AS HAIKU (MANDATORY — Task 1752)

**Before ANYTHING else, confirm you started with:**
```bash
claude --model claude-haiku-4-5-20251001
```

**Why:** Sessions running Sonnet burn 5x tokens. Incident 2026-06-18 cost Billy 4 hours and significant budget. Every session MUST start with the Haiku model command above.

**Verification:** If you're already in the session, you cannot change models. If running Sonnet, STOP immediately — exit and restart with Haiku.

---

## 1. Pull Latest State
```bash
git -C /opt/YOUR-PROJECT pull --rebase origin main
```
**Expected:** "Already up to date." or fast-forward merge
**If conflicts:** STOP. Resolve before proceeding.

## 2. Branch Verification
```bash
git -C /opt/YOUR-PROJECT branch --show-current
```
**Expected:** `main`
**If other branch:** `git -C /opt/YOUR-PROJECT checkout main && git pull`

## 3. Environment Verification
```bash
bash /opt/YOUR-PROJECT/ops/bootstrap/session-bootstrap.sh
```
**Expected:** All checks PASS. Exit 0.
**If failures:** Check docs/runbooks/SERVICE_RESTARTS.md for the failing service.

## 4. Recover Stale Tasks (MANDATORY)
```bash
python3 /opt/YOUR-PROJECT/ops/agent/recover-stale-tasks.py --check
```
**Expected:** "No stale tasks found." 
**If stale tasks found:** Run `--recover-all` to reset them to pending.
```bash
python3 /opt/YOUR-PROJECT/ops/agent/recover-stale-tasks.py --recover-all
```
**Why:** Prevents accumulated in_progress tasks from blocking new work. MUST run before claiming any task.

## 5. Read Current State
```bash
cat /opt/YOUR-PROJECT/system-map/CURRENT_STATE.md
```
Focus on: KNOWN ISSUES, PENDING sections.

## 6. Task Discovery
```bash
bash /opt/YOUR-PROJECT/ops/agent/list-tasks.sh pending
```
**Expected:** List of pending tasks with IDs.
**If empty:** All tasks complete — check CURRENT_STATE.md for next priorities.

## 7. Claim a Task
```bash
eval $(bash /opt/YOUR-PROJECT/ops/agent/run-task.sh <AGENT_NAME>)
echo "Claimed: $TASK_ID — $TASK_TITLE"
echo "Worktree: $TASK_WORKTREE"
```
**Expected:** TASK_ID, TASK_TITLE, TASK_LAYER, TASK_WORKTREE exported.

## 8. Verify Task Before Starting
```bash
python3 /opt/YOUR-PROJECT/ops/agent/validate-task.py $TASK_ID
```
**Expected:** `VALID: task 0XXX`
**If INVALID:** Do NOT proceed. Report to orchestrator via mailbox.

## 9. Work and Verify
- Work in $TASK_WORKTREE (git worktree for isolation)
- Check CONTEXT.md if any terminology is unclear
- Check GOLDEN_RULES.md before any destructive action
- Verify every change: curl, git log, docker inspect — never "should work"

## 10. Completion Expectations
```bash
bash /opt/YOUR-PROJECT/ops/agent/complete.sh $TASK_ID "What was done" "commit_hash_or_evidence"
```
Evidence MUST be: a commit hash, a curl output, a file path, or a test result.
Never: "I believe it works" or "should be fine".

## 11. Escalation Protocol
Escalate to orchestrator when:
- Same failure 3 times in a row
- Task requires Billy decision (security-sensitive, architecture change)
- Task is blocked by another task's failure
- Mailbox has a message: `python3 /opt/YOUR-PROJECT/ops/agent/mailbox.py read <AGENT_NAME>`

```bash
python3 /opt/YOUR-PROJECT/ops/agent/mailbox.py send orchestrator <AGENT_NAME> escalation \
  "Task $TASK_ID blocked: <reason>"
```

## Advanced Stale Task Handling
If a task from a previous session goes stale mid-work (session interrupted):
```bash
python3 /opt/YOUR-PROJECT/ops/agent/recover-stale-tasks.py --recover $TASK_ID
```
(Note: Step 4 above already handles bulk recovery automatically at boot.)
