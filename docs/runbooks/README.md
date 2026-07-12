---
doc_type: runbook
last_updated: 2026-07-06
ssot_status: CURRENT
audience: all-agents
---

# docs/runbooks/ — Runbook Index

All operational procedures for diagnosing and recovering [YOUR-AI-NAME] V8 services.

---

## Contract and guard (task E0000000010/E0000000012)

Every runbook should follow `docs/runbooks/TEMPLATE.md`'s structure: Problem Statement,
Diagnosis (30 seconds), Root Causes, Resolution Steps, Rollback, Evidence, Related. New or
already-migrated runbooks are validated against this by `ops/agent/runbook_guard.py` (run via
`python3 ops/agent/runbook_guard.py` or `python3 -m pytest ops/tests/test_runbook_guard.py -q`).

Migration is grandfathered, not forced: a runbook without YAML frontmatter is reported as
non-blocking migration debt, not hard-failed — rewriting each not-yet-migrated runbook's
technical content correctly requires verifying its facts against live system state first (a
real, careful, per-file task, not something to force through a script).

## Runbooks

| Runbook | Covers | Status |
|---|---|---|
| [OPERATOR-RUNBOOKS.md](OPERATOR-RUNBOOKS.md) | Gate failures, approval gates, dependencies, drift, email | ✅ created 2026-07-06 |
| [docker-health.md](docker-health.md) | Container health checks, restart procedures | ✅ migrated + verified 2026-07-03 |
| [telegram-debug.md](telegram-debug.md) | Telegram bot diagnosis, OpenClaw issues | ✅ migrated + verified 2026-07-03 |
| [memory-recovery.md](memory-recovery.md) | ChromaDB + PostgreSQL recovery | ✅ migrated + verified 2026-07-03 |
| [domain-access.md](domain-access.md) | Nginx + [your-domain.com] routing issues | ✅ migrated + verified 2026-07-03 |
| [incident-response.md](incident-response.md) | Multi-layer incident workflow | ✅ migrated + verified 2026-07-03 |
| [BACKUPS.md](BACKUPS.md) | Backup schedule + restore procedures | ✅ migrated + verified 2026-07-03 |
| [WARM_COLD_SESSION.md](WARM_COLD_SESSION.md) | Warm/cold model routing, warmup monitor | ✅ migrated + verified 2026-07-03 |
| [venzarai-router-routing.md](venzarai-router-routing.md) | VenzariAI Router health, auth, model routing | ✅ new runbook, created 2026-07-03 |
| [PERFORMANCE_FIXES.md](PERFORMANCE_FIXES.md) | Performance fixes deployed 2026-05-27 | migration debt |

**ssh-tunnel.md removed (2026-07-03, task E0000000012):** described a two-VPS SSH tunnel
architecture that no longer exists — confirmed live, `venzarai-tunnel.service` and
`ssh-tunnel-watchdog.service` are both gone under the current single-consolidated-VPS
architecture. Archived to `docs/archive/dead-runbooks/ssh-tunnel.md` for historical reference.

**Real operational gaps found during this migration pass (2026-07-03), not fixed here —
flagged for follow-up:**
- claude-mem (`claude-mem-claude-mem-server-1`/`-worker-1`) is actively crash-looping with
  `getaddrinfo ENOTFOUND` — already tracked as Phase 8 task `L0000000005`.
- PostgreSQL backups are real and current (`/opt/backups/postgresql/`, daily, verified today's
  file exists) but appear to be **local-only** — no working offsite sync remote was found
  (only a `jeanne-b2:` rclone remote exists, no `jeanne-r2:`, and the currently-running backup
  script `/tmp/backup-postgres.sh` doesn't obviously push offsite). See `BACKUPS.md`.

---

## Which Runbook Do I Need?

| Symptom | Runbook |
|---|---|
| Telegram bot not responding | telegram-debug.md |
| VenzariAI Router timeout / model not loading | venzarai-router-routing.md |
| Container crashed / not healthy | docker-health.md |
| [your-domain.com] unreachable | domain-access.md |
| Database query errors | memory-recovery.md |
| Multiple systems down | incident-response.md |
| Backup not running | BACKUPS.md |
| Slow/unresponsive model, warmup monitor issues | WARM_COLD_SESSION.md |
