# Context — [PROJECT NAME]

> Read this at the start of every session. Keep it up to date.

**Last updated:** [FILL IN: date]
**Updated by:** [FILL IN: who/what updated this]

---

## What This Project Does

[FILL IN: 2-3 sentence description of what this project is, what it does, and who uses it.]

## Current Status

[FILL IN: What phase is the project in? What was last completed? What's next?]

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| [FILL IN] | e.g. Node.js | e.g. 22.x |
| [FILL IN] | e.g. PostgreSQL | e.g. 16 |
| [FILL IN] | e.g. Redis | e.g. 7 |
| [FILL IN] | e.g. Nginx | e.g. 1.25 |

---

## Running Services

[FILL IN: List all services that should be running. Use ✅ for running, ❌ for stopped.]

- ✅ [SERVICE NAME] — port [PORT] — [brief description]
- ❌ [SERVICE NAME] — [brief description]

See `system-map/CURRENT_STATE.md` for live state.

---

## API Keys Required

[FILL IN: List which API keys are needed. NEVER put values here — only key names.]

- `OPENAI_API_KEY` — [used for what]
- `GITHUB_TOKEN` — [used for what]

---

## Active Hotspots (Things to be careful about)

[FILL IN: What areas of the codebase are fragile, being refactored, or need special care?]

- [e.g., "auth module is being refactored — don't touch src/auth/ without reading ADR-005"]
- [e.g., "production database migration pending — coordinate before any DB changes"]

---

## Current Sprint / Active Work

[FILL IN: What is the team working on right now?]

---

## Key Files

| File | Purpose |
|------|---------|
| `GOLDEN_RULES.md` | Engineering rules for this project |
| `SESSION_STARTUP.md` | Read before every session |
| `system-map/CURRENT_STATE.md` | Live running state |
| `.tasks/` | Active tasks (JSON) |
| `docs/adr/` | Architecture decisions |

---

*Keep this file updated. VENZARI CODE reads it at every session start.*
