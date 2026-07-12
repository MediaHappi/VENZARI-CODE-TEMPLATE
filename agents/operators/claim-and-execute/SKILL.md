---
name: "claim-and-execute"
description: "Operator: full session startup to task completion. Composes mandatory session startup → claim-task → inject_context → [task-selected-skill] → task-completion-verifier. Use at the start of every agent session."
version: "1.0"
type: operator
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
composed-skills:
  - claim-task
  - task-completion-verifier
---

## Brief

**Operator: claim-and-execute** — mandatory session startup to completion.

When to use:
- Start of EVERY agent session (no exceptions — CLAUDE.md Rule)
- After completing a task and picking up the next one

Do NOT use when: you're mid-task (don't re-claim).

## Skills

### Step 0 — Mandatory session startup (before claiming)

```bash
git -C /opt/YOUR-PROJECT pull
bash /usr/local/bin/jeanne-bootstrap-check
cat /opt/YOUR-PROJECT/system-map/CURRENT_STATE.md
```

### 1. `claim-task`

Claim the next pending task, read its required skills.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py claim <AGENT_ROLE>
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load <required-skill-from-task>
```

### 2. inject_context

Inject all memory layers for the claimed task.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "<task title>"
```

### 3. Execute with task-selected skill

Load and run whatever skill the task requires. Complete the DoD items.

### 4. `task-completion-verifier`

Verify every DoD item with real commands before marking complete.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load task-completion-verifier
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py complete <task_id> "<summary>" --evidence "<curl output>"
```

## Failure handling

Bootstrap check failures → fix before claiming.
Three task failures → load `escalate` skill, write to `.team/inbox/billy.jsonl`.

---

## Detail

See `## Skills` section above for the complete step sequence. Each composed skill has its own
`## Detail` section with full commands and verification steps.

---

## Reference

### Failure handling

If any composed skill fails 3 times → load `escalate` skill (Rule 7).
Write failure to `.team/inbox/billy.jsonl` before stopping.

### Doc Impact

| Doc | What to update |
|---|---|
| `system-map/CURRENT_STATE.md` | Update service state if any deploy was made |
