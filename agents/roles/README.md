# agents/roles/

**Status:** RESERVED — Agent role policy definitions (future expansion)  
**Owner:** [YOUR-AI-NAME] Orchestrator

---

## Purpose

This directory will hold per-role behavioral policies for specialist agents:
- What each agent type is allowed to do
- What operations require escalation to Billy
- Capability boundaries (e.g., infrastructure agent cannot touch app code)

---

## Current Roles (Defined in CLAUDE.md)

| Role | Agent Type | Capability |
|---|---|---|
| discovery | Scan repos, map services, read-only | No writes |
| infrastructure | VPS infra, Docker, Nginx, SSH, cron | Venzari VPS only |
| backend | Flask controllers, APIs, Celery | Read + write app code |
| frontend | Dashboard UI, templates | Read + write UI code |
| devops | Deployments, rollbacks, git tags | Commit + push |
| testing | Endpoint verification, health checks | Read + curl only |
| security | Secret detection, permission audits | Read only |
| data | PostgreSQL, Redis, ChromaDB | Read only (no writes) |
| memory | Session compression, changelog | Write CURRENT_STATE + changelog |

---

## Future: Role Policy Files

When a role needs formal boundaries documented:
1. Create `<role-name>.md` in this directory
2. Define: capabilities, forbidden operations, escalation triggers
3. Reference from PROJECT_OVERLAY.md
