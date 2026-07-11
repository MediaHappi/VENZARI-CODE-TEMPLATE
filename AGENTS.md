# AGENTS.md — Team Registry

> This file registers the human engineers and automated agents working in this project.
> VENZARI CODE reads this at session start to understand who/what is operating.

---

## Human Team Members

| Name | Role | GitHub | Timezone |
|------|------|--------|----------|
| [FILL IN] | [e.g., Lead Engineer] | @[username] | [e.g., UTC-5] |

---

## Automated Agents

| Agent | Runtime | Mode | Scope |
|-------|---------|------|-------|
| venzari-code | VENZARI CODE CLI | discover/implement/validate | This repo |

---

## Session Ownership

Each session must have a clear owner. When starting a session:

```bash
# Human-driven session
venzari-code start . --mode implement

# Autonomous daemon session (review before running)
venzari-code daemon . --budget 5 --role implement
```

---

## Escalation

If a task is blocked or unclear:
1. Check `CONTEXT.md` — is the answer there?
2. Check `docs/adr/` — was a decision already made?
3. Stop the session and leave a note in the task description
4. [FILL IN: escalation contact / channel]

---

*Keep this file updated as team members join or leave.*
