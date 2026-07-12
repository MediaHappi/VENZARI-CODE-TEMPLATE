# CURRENT_STATE.md — System Map

**Document Class:** Operational (Layer 3)
**Update Frequency:** Every session — agents MUST update this
**Authority:** [Your Name] ([your-email])
**Last Updated:** [FILL IN — YYYY-MM-DD]
**Updated by:** [FILL IN — agent role or human]

This is the **single source of runtime truth**. Not the README. Not your memory. THIS FILE.
If you don't know the current state of the system, read this file before doing anything else.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project name** | [FILL IN] |
| **AI name** | [FILL IN — e.g., "Aria"] |
| **Domain** | [FILL IN — e.g., "yourproject.com"] |
| **VPS / host** | [FILL IN — e.g., "123.456.789.0"] |
| **Repo path (live)** | [FILL IN — e.g., "/opt/YOUR-PROJECT"] |
| **Repo remote** | [FILL IN — e.g., "github.com/your-org/your-project"] |

---

## 2. Service Status

| Service | Status | Port | Notes |
|---|---|---|---|
| [Main API] | [UP / DOWN / UNKNOWN] | [PORT] | [FILL IN] |
| [Worker] | [UP / DOWN / UNKNOWN] | — | [FILL IN] |
| [Database] | [UP / DOWN / UNKNOWN] | [PORT] | [FILL IN] |
| [Cache / Redis] | [UP / DOWN / UNKNOWN] | [PORT] | [FILL IN] |
| [AI router] | [UP / DOWN / UNKNOWN] | [PORT] | [FILL IN] |

---

## 3. Active Tasks

| Task ID | Title | Status | Assigned to | Worktree |
|---|---|---|---|---|
| [FILL IN] | [FILL IN] | [pending / in_progress / blocked] | [role] | [branch or —] |

**Task backlog:** `python3 ops/agent/task_manager.py list`

---

## 4. Last 5 Completed Tasks

| Task ID | Title | Completed | Evidence |
|---|---|---|---|
| [FILL IN] | [FILL IN] | [YYYY-MM-DD] | [key commit / test output] |

---

## 5. Known Issues / Blockers

| # | Issue | Severity | Since | Notes |
|---|---|---|---|---|
| 1 | [FILL IN] | [critical / high / medium / low] | [YYYY-MM-DD] | [FILL IN] |

---

## 6. Environment Variables Required

| Variable | Where set | Notes |
|---|---|---|
| [FILL IN] | `.env` / systemd | [FILL IN] |

---

## 7. Deployment State

| Component | Last deployed | Commit | By |
|---|---|---|---|
| [FILL IN] | [YYYY-MM-DD] | [short hash] | [agent / human] |

---

## 8. Agent Sessions (last 3)

| Date | Role | Tasks completed | Key actions |
|---|---|---|---|
| [YYYY-MM-DD] | [role] | [TASK-XXX, ...] | [FILL IN] |

---

## 9. Memory Layers

| Layer | Status | Last write | Notes |
|---|---|---|---|
| 00-foundation | [FILL IN] | [YYYY-MM-DD] | VPS, SSH, Nginx, cron |
| 01-intelligence | [FILL IN] | [YYYY-MM-DD] | Code graph, analysis |
| 02-memory | [FILL IN] | [YYYY-MM-DD] | Memory schema |
| 03-workflow | [FILL IN] | [YYYY-MM-DD] | Task system, skills |
| 04-ethical | [FILL IN] | [YYYY-MM-DD] | Governance, SOUL |
| 05-monitoring | [FILL IN] | [YYYY-MM-DD] | Alerts, health |

---

## 10. How to Read This File

Every agent session MUST:
1. `cat system-map/CURRENT_STATE.md` — read before acting
2. `cat GOLDEN_RULES.md | head -30` — re-read rules
3. Update this file with task completions, new issues, and state changes
4. Run `python3 ops/agent/task_manager.py list` to confirm task state

*Updated by VENZARI CODE template — venzari.dev*
