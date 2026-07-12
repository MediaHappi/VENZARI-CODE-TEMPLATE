# Agent Communication Protocol

**Version:** 1.0  
**Last updated:** 2026-05-27

This document defines the actual wire protocol used by [YOUR-AI-NAME] agents for coordination. Implementation: `ops/agent/mailbox.py`, `ops/agent/claim.sh`, `ops/agent/hitl_wait.sh`.

---

## Mailbox Format

Mailboxes are JSONL files at `.team/inbox/{agent_name}.jsonl`.

Each line is one JSON message object. Messages are append-only — never edit or delete lines.

### Required Fields

| Field | Type | Description |
|---|---|---|
| `from` | string | Sending agent name or "billy" for human messages |
| `to` | string | Receiving agent name or "billy" for HITL messages |
| `type` | string | Message type (see below) |
| `content` | string or object | Message payload |
| `ts` | string | ISO 8601 timestamp (UTC) |

### Optional Fields

| Field | Type | Description |
|---|---|---|
| `task_id` | string | Related task ID (e.g. "0012") |
| `group_id` | string | Convergence group ID |
| `evidence` | string | Proof of completion (curl output, file path, etc.) |

### Example Message

```json
{"from":"backend","to":"billy","type":"escalate","content":"Three identical failures on task 0014 — SSH tunnel not responding","task_id":"0014","ts":"2026-05-27T14:32:00Z"}
```

---

## Message Types

| Type | Direction | Meaning |
|---|---|---|
| `task_claim` | agent → billy | Agent has claimed a task (informational) |
| `task_complete` | agent → orchestrator | Task completed with evidence |
| `task_failed` | agent → orchestrator | Task failed — describe cause |
| `escalate` | agent → billy | Three identical failures — needs human decision |
| `shutdown_request` | orchestrator → agent | Request graceful shutdown |
| `shutdown_response` | agent → orchestrator | Acknowledging shutdown, current task state |
| `plan_request` | orchestrator → agent | Request a work plan before starting |
| `plan_response` | agent → orchestrator | Responding with proposed plan |

---

## Claiming Protocol

Task claiming uses `fcntl.LOCK_EX` (exclusive file lock) to prevent race conditions.

```bash
# Shell interface
bash /opt/YOUR-PROJECT/ops/agent/claim.sh

# What it does:
# 1. Acquires fcntl.LOCK_EX on .tasks/.claim_lock
# 2. Scans .tasks/*.json for status=pending with no blocked_by dependencies
# 3. Sets status=in_progress, assigned_to=<agent_name>, claimed_at=<timestamp>
# 4. Releases lock
# 5. Exports TASK_ID, TASK_TITLE, TASK_LAYER to environment
```

Rules:
- Never manually edit a task to in_progress — always use claim.sh
- After context compression, re-read your `.tasks/{task_id}.json` to restore identity
- If you find your own task in in_progress with no recent activity, it may be stale — use `ops/agent/recover-stale-tasks.py`

---

## Convergence Pattern

For parallel tasks that must all complete before a downstream task starts:

1. Create all parallel tasks with unique `group_id`
2. Create a convergence task with `blocked_by: [id1, id2, id3]`
3. Each parallel task sets its own status to `completed`
4. The convergence task becomes claimable only when all blocked_by tasks are `completed`

```json
{"id":"0030","title":"Synthesize results","status":"pending","blocked_by":["0026","0027","0028"],"group_id":"container-audit"}
```

---

## HITL Checkpoint

When a task requires human approval before proceeding:

```bash
bash /opt/YOUR-PROJECT/ops/agent/hitl_wait.sh "Task 0017: Ready to write to /usr/local/bin on Venzari VPS. Approve? (y/n)" 0017
```

This appends an `escalate` message to `.team/inbox/billy.jsonl` and blocks until Billy responds via the inbox.

HITL is mandatory for:
- Any write to `/usr/local/bin` or system directories
- Any change to OpenClaw config
- Any `docker restart` of a running container
- Any change to VenzariAI Router model groups

---

## Context Restoration After Compaction

When Claude Code compacts the context, the session loses its task identity. Restore it:

```bash
# 1. Re-read your task
cat /opt/YOUR-PROJECT/.tasks/${TASK_ID}.json

# 2. Re-read role context
cat /opt/YOUR-PROJECT/CLAUDE.md
cat /opt/YOUR-PROJECT/GOLDEN_RULES.md

# 3. Check your inbox for pending messages
python3 /opt/YOUR-PROJECT/ops/agent/mailbox.py read ${AGENT_NAME}
```

---

## Escalation Rule

**Stop on three identical failures.** If the same operation fails three times with the same error:

1. Write to `.team/inbox/billy.jsonl` with type `escalate`
2. Set task status to `failed` with the error description
3. Do not attempt a fourth time
4. Wait for human decision

```json
{"from":"infrastructure","to":"billy","type":"escalate","content":"SSH tunnel fails 3x: Connection refused on port 37877. Tried: systemctl restart, manual ssh -L, verified Venzari VPS is up. Need manual inspection.","task_id":"0002","ts":"2026-05-27T15:00:00Z"}
```
