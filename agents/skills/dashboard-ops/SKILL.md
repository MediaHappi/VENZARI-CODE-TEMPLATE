---
name: dashboard-ops
description: |
  Operate and maintain [YOUR-AI-NAME] Dashboard V8 (Laravel 11 + React 19 + Inertia.js) on Venzari VPS at :5010. Use for health checks, queue worker ops, route/controller changes, and migration runs.
version: "3.0"
compatible-roles:
  - backend
  - infrastructure
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Dashboard Operations

> **Version:** 3.0 | **Last verified:** 2026-06-20 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Maintain, debug, and develop [YOUR-AI-NAME] Dashboard V8 (Laravel 11 / Inertia.js / React 19 / TypeScript)
on Venzari VPS (single-node — no Venzari VPS, no Docker for the web app).

---

### When to Use

- Dashboard returning 500 or not loading
- Queue worker not processing jobs
- Adding a new Laravel route or controller
- Rebuilding frontend assets (npm run build)
- Running database migrations
- Debugging Redis or PostgreSQL issues

---

### Key Facts

| Item | Value |
|---|---|
| Web app | systemd: `jeanne-dashboard-v8` (127.0.0.1:5010) |
| Queue worker | systemd: `jeanne-dashboard-v8-worker` |
| Source | `/opt/[YOUR-AI-NAME]-DASHBOARD-V8/` (Laravel root) |
| SSOT config copies | `/opt/YOUR-PROJECT/ops/configs/dashboard-v8/` |
| PostgreSQL | `jeanne-dashboard-v8-db-1` container (:5432) |
| Redis | system Redis (:6379) |
| AI routing | VenzariAI Router 127.0.0.1:4001 (no jeanne-bridge) |
| URL | nginx -> 127.0.0.1:5010 |

---

## Detail

### Health check

```bash
# Quick HTTP check
curl -sw '\nHTTP:%{http_code}' http://127.0.0.1:5010/ 2>/dev/null | grep HTTP

# Full service health (all 6 services)
curl -s http://127.0.0.1:5010/api/health/status | python3 -m json.tool | head -30

# Check systemd status
sudo systemctl status jeanne-dashboard-v8 jeanne-dashboard-v8-worker

# Check Laravel log for errors
tail -20 /opt/[YOUR-AI-NAME]-DASHBOARD-V8/storage/logs/laravel.log | grep -i "ERROR\|CRITICAL"
```

### Restart services

```bash
# Clear config cache + restart (do this after any config/env change)
cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8
php artisan config:clear && php artisan config:cache
sudo systemctl restart jeanne-dashboard-v8 jeanne-dashboard-v8-worker
```

### Add or edit a Laravel route/controller

```bash
# 1. Edit source on Venzari VPS directly
cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8
# Edit routes/api.php or app/Http/Controllers/Api/<Name>Controller.php

# 2. Clear route cache
php artisan route:clear && php artisan route:cache

# 3. Verify
curl -s -o /dev/null -w "HTTP:%{http_code}\n" http://127.0.0.1:5010/api/<route>
```

### Rebuild frontend assets

```bash
cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8
npm run build
# Output goes to public/build/ -- commit public/build/ to [YOUR-AI-NAME]-DASHBOARD-V8 repo
sudo systemctl restart jeanne-dashboard-v8
```

### Debug queue worker not running

```bash
# Check worker logs
sudo journalctl -u jeanne-dashboard-v8-worker --tail 50

# Check Redis
redis-cli ping  # -> PONG

# Restart worker
sudo systemctl restart jeanne-dashboard-v8-worker
```

### Run database migration

```bash
cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8
php artisan migrate --force
# Verify
php artisan migrate:status | tail -5
```

### Commit changes to GitHub

```bash
cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8
git add app/ config/ resources/ routes/ public/build/
git commit -m "fix: <summary>"
git push origin main
```

---

### Verification

```bash
curl -sw '\nHTTP:%{http_code}' http://127.0.0.1:5010/ 2>/dev/null | grep HTTP
# Must be HTTP:200
sudo systemctl is-active jeanne-dashboard-v8 jeanne-dashboard-v8-worker
# Both must be: active
```

---

## Reference

### Failure Runbook

| Symptom | Fix |
|---|---|
| HTTP 500 | `tail -50 storage/logs/laravel.log`, fix code, clear cache, restart |
| Queue job stuck | Check worker logs (`journalctl -u jeanne-dashboard-v8-worker`), restart worker |
| Redis connection error | `redis-cli ping`, start Redis if down |
| Database error | Check PostgreSQL container, run `php artisan migrate --force` |
| Frontend stale | `npm run build`, commit public/build/, restart dashboard |
| CRITICAL config log | Check `.env` has all vars, run `php artisan config:clear && config:cache` |
| VenzariAI Router 404 | `curl http://127.0.0.1:4001/health/liveliness` -- restart router if down |

### What NOT to use

- No Docker for the web app (systemd only)
- No `flask db upgrade`, no Celery -- this is Laravel
- No Venzari VPS SSH -- single VPS, work directly on Venzari VPS
- No jeanne-bridge -- BrainService.php calls VenzariAI Router :4001 directly
