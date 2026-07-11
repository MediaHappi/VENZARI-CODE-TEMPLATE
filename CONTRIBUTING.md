# Contributing — [PROJECT NAME]

> How to work effectively in a VENZARI CODE governed project.

---

## Workflow

Every change follows the same lifecycle:

```
discover → plan → implement → validate → review → commit
```

1. **Discover** — Run `venzari-code start . --mode discover` to understand current state
2. **Plan** — Understand what needs to change before touching any files
3. **Implement** — Make the changes. Stay in scope of your claimed task.
4. **Validate** — Run tests. All must pass. Record output as evidence.
5. **Review** — Check the diff. Nothing unrelated should change.
6. **Commit** — Write a clear commit message. Complete the task.

---

## Task Lifecycle

```bash
# See all pending tasks
ls .tasks/

# Claim a task
venzari-code claim PROJ-001-your-task --role implement

# Complete a task (requires evidence)
venzari-code complete PROJ-001-your-task \
  --summary "Added feature X — 3 files changed" \
  --evidence "Tests: 42 pass. Typecheck clean." \
  --skill implement
```

---

## Evidence Requirements

Every task completion requires **at least 3 evidence events** recorded during the session:
- Test run output (pass count)
- File changes (what was edited)
- Verification (manual check or automated assertion)

---

## Code Standards

- Follow the existing style in each file
- Parameterized queries only — no string interpolation in SQL or shell
- `{env:VAR}` syntax for all secret references in config files
- Tests must pass before any commit
- Update `CONTEXT.md` and `system-map/CURRENT_STATE.md` when relevant

---

## Creating New Tasks

Add a JSON file to `.tasks/`:

```json
{
  "id": "PROJ-002-descriptive-name",
  "title": "Short description (< 60 chars)",
  "priority": "high",
  "description": "What needs to be done, why, and any context",
  "status": "pending"
}
```

---

## ADRs (Architecture Decision Records)

When making a significant architectural decision, create an ADR in `docs/adr/`:

```
docs/adr/ADR-001-decision-title.md
```

Use the template at `docs/adr/ADR-TEMPLATE.md`.

---

*This project uses VENZARI CODE for session management, tool governance, and evidence-based task completion.*
