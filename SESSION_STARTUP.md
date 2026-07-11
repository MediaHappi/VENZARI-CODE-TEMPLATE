# Session Startup

> Read this at the start of every VENZARI CODE session.

---

## Before You Start

1. Read `CONTEXT.md` — understand current project state
2. Read `system-map/CURRENT_STATE.md` — check what services are running
3. Check `.tasks/` — what's pending? What was last completed?
4. Read the most recent handoff in `.venzari/handoffs/` if one exists

## Start the Session

```bash
# From the project root
venzari-code start . --mode discover
```

Then transition to your working mode:
- `--mode plan` — for planning new work
- `--mode implement` — for building features
- `--mode validate` — for testing
- `--mode review` — for reviewing changes
- `--mode commit` — for completing and committing

## Task Workflow

```bash
# 1. See available tasks
venzari-code list-repos

# 2. Claim a task
venzari-code claim <task-id> --role implement

# 3. Do the work (in the session)

# 4. Complete the task
venzari-code complete <task-id> \
  --summary "What was done" \
  --evidence "Tests: X pass. Files changed: Y." \
  --skill test
```

## End of Session

VENZARI CODE automatically writes a handoff document to `.venzari/handoffs/` when you stop the session (Ctrl+C or session end). The next session starts by reading that handoff.

---

## Current Phase

**Phase:** [FILL IN: e.g., Phase 1 — Foundation]
**Status:** [FILL IN: e.g., In Progress]
**Next task:** [FILL IN: e.g., PROJ-001-setup-database]

---

*Keep this file updated. It is the first thing read at every session.*
