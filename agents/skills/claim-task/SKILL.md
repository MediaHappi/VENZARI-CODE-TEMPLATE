---
name: claim-task
description: |
  Mandatory session start skill. Claims the next available task, injects all 6 memory layers, reads required skills and agent role, then begins work. Use at the start of EVERY agent session, after completing a task, or when told to pick up the next task.
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
allowed-tools: Bash, Read
---

# Skill: Claim Task

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Mandatory session start skill. Atomically claim the next available task, inject all 6 memory
layers including skill hints (Layer 0), read the task's required skills and agent role, load
those skills, then begin work. DO NOT skip skill loading — it contains the procedures you need.

---

### When to Use

- At the start of EVERY agent session (no exceptions)
- After completing a task and looking for the next one
- When told "pick up the next task" or "claim a task"

---

---

## Detail

### Process

### Step 0 — Mandatory session startup (BEFORE claiming)

```bash
git -C /opt/YOUR-PROJECT pull
cat /opt/YOUR-PROJECT/system-map/CURRENT_STATE.md
cat /opt/YOUR-PROJECT/GOLDEN_RULES.md | head -30
```

Do not skip. If you skip this, you are working blind (CLAUDE.md Rule 1).

---

### Step 1 — List available tasks

```bash
bash /opt/YOUR-PROJECT/ops/agent/list-tasks.sh pending
```

Note tasks with `blocked_by` — they cannot be claimed until dependencies complete.

---

### Step 2 — Claim the next task

```bash
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py claim <AGENT_NAME>
```

The claim is atomic (file-locked). Record the returned task JSON especially:
- `id` — task identifier
- `agent_role` — which role policy applies to this task
- `required_skills` — skills you MUST load before starting
- `dod` — your completion contract

---

### Step 3 — Get Layer 0 skill hints (NEW — Rule 15)

```bash
python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "<task title>" --layers l0
```

This shows which skills are relevant for this task type. Read the output.

---

### Step 4 — Read your role policy (Rule 14)

```bash
# Use the agent_role from the task JSON
cat /opt/YOUR-PROJECT/agents/roles/<agent_role>.md
```

This tells you: what you CAN do, what is FORBIDDEN, escalation triggers, primary skills.

---

### Step 5 — Load required skills (Rule 15 — MANDATORY)

```bash
# Load each skill from required_skills in the task JSON
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load <skill-name>
```

**DO NOT skip this step.** The skill contains:
- The exact procedure to follow (not guesswork)
- The verification commands for each step
- The failure runbook if something goes wrong

If required_skills is empty, consult SKILL_CATALOG quick reference:
```bash
head -30 /opt/YOUR-PROJECT/agents/SKILL_CATALOG.md
```

---

### Step 5.5 — Start the Task Executor (NEW — 2026-07-05, evidence tracking)

After loading skills, start the task executor. It prints the full skill procedure checklist
and tracks evidence as you work — so you don't need to reconstruct it at close.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/task_executor.py start <TASK_ID>
```

**During work** — record each meaningful action→outcome pair:
```bash
python3 /opt/YOUR-PROJECT/ops/agent/task_executor.py evidence <TASK_ID> "curl :4001 → 200 OK"
python3 /opt/YOUR-PROJECT/ops/agent/task_executor.py evidence <TASK_ID> "git commit abc1234 pushed"
```

**At close** — get formatted evidence ready for --evidence flag:
```bash
python3 /opt/YOUR-PROJECT/ops/agent/task_executor.py collect <TASK_ID>
```

Why: 297 skills exist in agents/skills/. The executor prints the actual skill procedure
so agents follow it instead of just naming it. Evidence gathered during work is always
better than evidence reconstructed at close.

---

### Step 6 — Inject 6-layer memory context

```bash
python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "<task title and key tags>"
```

Queries: L0 skills, L4 codegraph (code structure), L3 claude-mem (history),
L5 decision-log (ADRs), L5 GOLDEN_RULES. Each layer is non-blocking.

---

### Step 7 — Write down your DOD

Extract the `dod` array from the task JSON. Write each item down.
These are your completion contract — you cannot mark complete without satisfying each one.

---

### Step 8 — Set up working environment

For >2 files or any infra change: use `worktree-task` skill first.
For simple tasks: work directly in `/opt/YOUR-PROJECT`.

---

### Rationalizations (and why they're wrong)

| Excuse | Rebuttal |
|---|---|
| "I know what needs to be done, I don't need to check tasks." | The queue reflects Billy's priorities. List first. |
| "Memory injection failed, I'll skip it." | Each layer is non-blocking — try it, gracefully skips unavailable. |
| "I'll skip skill loading, I know how to do this." | Skills contain the current procedure. The infra may have changed. |
| "I don't need to read the role policy." | It tells you what you're FORBIDDEN from doing. Missing this causes incidents. |
| "The DOD items are obvious, I won't write them down." | Agents 10 messages into a session forget the DOD. Write it now. |

---

### Red Flags — Stop and Escalate

- Zero available tasks: do not proceed without a task (Rule 8)
- Task `failure_count` is 3: do not claim it — escalate to Billy via `.team/inbox/billy.jsonl`
- `required_skills` lists a skill that doesn't exist in skill_loader: create a task to build it

---

### Verification

Claim is complete when all of these are true:

```bash
# Task claimed (JSON shows "status": "in_progress")
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py status <TASK_ID>

# Skills loaded (no error from skill_loader.py)
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load <required_skill>

# Memory context retrieved (shows === INJECTED MEMORY CONTEXT ===)
python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "<task title>"

# DOD items written down and understood
```

---

### Related Skills

- `worktree-task` — use for >2 files or infra changes
- `memory-write` — use at task completion
- `escalate` — use if failure_count hits 3

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

