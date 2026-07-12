---
inclusion: always
---

# Tech Steering

## Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | [FILL IN — e.g., "TypeScript / Python"] | [FILL IN] |
| Runtime | [FILL IN — e.g., "Bun / Node 20"] | [FILL IN] |
| Framework | [FILL IN — e.g., "Express / FastAPI"] | [FILL IN] |
| Database | [FILL IN — e.g., "PostgreSQL / SQLite"] | [FILL IN] |
| Cache | [FILL IN — e.g., "Redis / Upstash"] | [FILL IN] |
| AI / LLM | [FILL IN — e.g., "Claude 3.5, LiteLLM router"] | [FILL IN] |
| Deploy | [FILL IN — e.g., "VPS + Docker / Fly.io"] | [FILL IN] |
| CI/CD | [FILL IN — e.g., "GitHub Actions"] | [FILL IN] |

## Conventions

- **Module system:** [FILL IN — e.g., "ESM only — no require()"]
- **TypeScript:** [FILL IN — e.g., "strict: true, exactOptionalPropertyTypes: true"]
- **Tests:** [FILL IN — e.g., "Bun test, must pass before every commit"]
- **Commits:** [FILL IN — e.g., "Conventional commits required"]
- **Branch model:** [FILL IN — e.g., "feature/* → main, no direct main pushes"]

## Architecture decisions

- [FILL IN — e.g., "ADR-001: Use SQLite for local state (no remote DB dependency)"]
- [FILL IN — e.g., "ADR-002: Stripe server-side only — CLI gets key activation only"]

## Patterns to follow

- [FILL IN — e.g., "Single source of truth for subscription state (syncToKV pattern)"]
- [FILL IN — e.g., "All agents use task_manager.py for task lifecycle — no shortcuts"]

## Patterns to AVOID

- [FILL IN — e.g., "No hardcoded paths — use PROJECT_DIR env var"]
- [FILL IN — e.g., "No partial webhook updates — always syncStripeDataToKV"]

## Key file paths

| What | Path |
|---|---|
| Main entry | [FILL IN] |
| Config | [FILL IN] |
| Task system | `ops/agent/task_manager.py` |
| Skills | `agents/skills/` |
| Memory layers | `00-foundation/` through `05-monitoring/` |
