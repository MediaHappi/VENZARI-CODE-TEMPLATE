# Layer 00 — Foundation Runbook

**Last updated:** 2026-05-30
**Layer stability:** LOCKED  
**Domain:** VPS infrastructure, SSH tunnel, Nginx, cron jobs, YOUR-PROJECT sync

---

## File Path Reference

### [your-vps-address]

| What | Path |
|---|---|
| OpenClaw config | `/home/billy/.openclaw/openclaw.json` |
| OpenClaw sessions | `/home/billy/.openclaw/agents/main/sessions/` |
| OpenClaw logs | `/home/billy/.openclaw/logs/` |
| YOUR-PROJECT repo | `/opt/YOUR-PROJECT` |
| Ops scripts (live) | `/usr/local/bin/` |
| Ops scripts (repo) | `/opt/YOUR-PROJECT/ops/venzari-vps/scripts/` |
| Systemd unit | `/etc/systemd/system/venzarai-tunnel.service` |
| Nginx config | `/etc/nginx/sites-enabled/[your-domain.com]` |
| Brain diagnostics | `/home/billy/diagnostics/` |
| Brain backups | `/home/billy/backups/` |

### [your-vps-address]

| What | Path |
|---|---|
| VenzariAI Router config | `/opt/venzarai-router/venzarai-router_config.yaml` |
| YOUR-PROJECT repo | `/opt/YOUR-PROJECT` |
| [YOUR-AI-NAME]-DASHBOARD | `/opt/[YOUR-AI-NAME]-DASHBOARD-V8` |
| Ollama models | `/usr/share/ollama/.ollama/models/` |
| Backups | `/home/billy/jeanne-backups/` |
| Live scripts | `/usr/local/bin/` |
| [your-vps-address]

---

## SSH Tunnel Operations

### Status check
```bash
systemctl status venzarai-tunnel.service
```

### Verify tunnel is passing traffic
```bash
curl -sf http://127.0.0.1:4001/health/liveliness && echo "TUNNEL OK" || echo "TUNNEL DOWN"
```

### Restart tunnel
```bash
systemctl restart venzarai-tunnel.service
sleep 3
curl -sf http://127.0.0.1:4001/health/liveliness && echo "OK"
```

### Deploy tunnel service (first time or after systemd unit update)
```bash
cp /opt/YOUR-PROJECT/ops/venzari-vps/systemd/venzarai-tunnel.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable venzarai-tunnel.service
systemctl start venzarai-tunnel.service
systemctl status venzarai-tunnel.service
```

**CRITICAL:** `ServerAliveInterval` must be `10` in the service unit. At 60s, stale channels take 180s to detect, causing ECONNRESET in OpenClaw. Never change it back to 60.

---

## YOUR-PROJECT Sync Health

### Manual sync
```bash
git -C /opt/YOUR-PROJECT pull --rebase origin main
```

### Check last sync time
```bash
git -C /opt/YOUR-PROJECT log -1 --format="%ar %s"
```

### Check sync cron is active
```bash
crontab -l | grep jeanne-cto-sync
# Expected: */15 * * * * /usr/local/bin/jeanne-cto-sync.sh
```

### Check [your-vps-address]
```bash
ssh venzari-vps-billy "git -C /opt/YOUR-PROJECT log -1 --format='%ar %s'"
```

---

## Cron Job Inventory ([your-vps-address]

| Schedule | Script | Purpose |
|---|---|---|
| `*/2 * * * *` | `jeanne-watchdog.sh` | SSH tunnel health check + restart |
| `*/2 * * * *` | `context-injector.py` | Writes MEMORY.md with fresh search results |
| `*/5 * * * *` | `jeanne-healthcheck.sh` | Detects stuck Ollama, auto-restarts with 15-min cooldown |
| `*/5 * * * *` | `post_response_sync.py` | Pushes chat entries to [your-vps-address]
| `*/5 * * * *` | `jeanne-session-cleanup.sh` | Removes stale .lock files |
| `*/10 * * * *` | `jeanne-ram-monitor.sh` | Telegram alert if [your-vps-address]
| `*/15 * * * *` | `jeanne-cto-sync.sh` | git pull YOUR-PROJECT |
| `*/30 * * * *` | `google_drive_sync.py` | Google Drive sync |
| `5 * * * *` | `venzarai-router-ram-patch.sh` | Patches jeanne-primary-coder:7b out of VenzariAI Router config (RAM guard) |
| `0 2 * * *` | `jeanne-backup.sh` | Daily backup |
| `0 3 * * *` | `jeanne-self-improve.sh` | Self-improvement pipeline |
| `0 3 * * 0` | `jeanne-cleanup.sh` | Weekly cleanup |
| `0 9 * * *` | `hubspot_acelle_sync.py` | HubSpot → Acelle sync |
| `15 8 * * *` | `proposals-gate.py` | Send pending proposals to Billy |
| `0 1 * * 0` | (log rotation) | Compress OpenClaw logs >200KB |

---

## Startup Sequence After Reboot

Run these in order on [your-vps-address]

```bash
# 1. Check SSH tunnel
systemctl status venzarai-tunnel.service
# If not running:
systemctl start venzarai-tunnel.service

# 2. Verify VenzariAI Router is reachable through tunnel
curl -sf http://127.0.0.1:4001/health/liveliness

# 3. Check OpenClaw container
docker ps | grep openclaw
# If not running (openclaw is on the venzari-vps-net bridge network, per GOLDEN_RULES.md Rule 3):
cd /opt/YOUR-OPENCLAW/docker && docker compose up -d

# 4. Verify Nginx
nginx -t && systemctl status nginx

# 5. Sync YOUR-PROJECT
git -C /opt/YOUR-PROJECT pull --rebase origin main

# 6. Check cron is running
systemctl status cron
```

---

## Nginx Operations

### Test config before reload
```bash
nginx -t
```

### Reload (after config change)
```bash
systemctl reload nginx
```

### Restart (required after listen address change)
```bash
systemctl restart nginx
```

**Rule:** nginx must listen on `0.0.0.0:80/443`. If you change it to `127.0.0.1`, a full `systemctl restart nginx` is required — reload is NOT enough to rebind sockets.

---

## Common Failures

### Failure: SSH tunnel is down (VenzariAI Router unreachable)

Symptom: OpenClaw responds with "Error connecting to VenzariAI Router" or Telegram gets no response.

```bash
systemctl status venzarai-tunnel.service
journalctl -u venzarai-tunnel.service -n 20
systemctl restart venzarai-tunnel.service
sleep 3
curl -sf http://127.0.0.1:4001/health/liveliness
```

### Failure: YOUR-PROJECT sync is stale (> 1 hour behind)

```bash
git -C /opt/YOUR-PROJECT fetch origin
git -C /opt/YOUR-PROJECT log HEAD..origin/main --oneline
git -C /opt/YOUR-PROJECT pull --rebase origin main
# Check cron:
crontab -l | grep jeanne-cto-sync
# If missing, add it:
(crontab -l; echo "*/15 * * * * /usr/local/bin/jeanne-cto-sync.sh >> /home/billy/.openclaw/logs/jeanne-cto-sync.log 2>&1") | crontab -
```

### Failure: cron not running

```bash
systemctl status cron
systemctl start cron
```

### Failure: Nginx 502 Bad Gateway on [your-domain.com]

```bash
# Check dashboard container on [your-vps-address]
ssh venzari-vps-billy "docker ps | grep dashboard"
# Check SSH tunnel for port 5002
curl -sf http://127.0.0.1:5002/ -o /dev/null -w "%{http_code}"
```

### Failure: OpenClaw container not running

```bash
docker ps | grep openclaw
# Find compose file:
find /opt/YOUR-OPENCLAW -name docker-compose.yml 2>/dev/null | head -5
# Start it (venzari-vps-net bridge network, per GOLDEN_RULES.md Rule 3):
cd /opt/YOUR-OPENCLAW/docker && docker compose up -d
docker logs jeannebrain-openclaw-v5 --tail 30
```

---

## Script Sync Verification

To check if live `/usr/local/bin/` scripts match repo versions:

```bash
for script in /opt/YOUR-PROJECT/ops/venzari-vps/scripts/*.sh; do
    base=$(basename "$script")
    live="/usr/local/bin/$base"
    if [ -f "$live" ]; then
        if diff -q "$script" "$live" > /dev/null 2>&1; then
            echo "OK   $base"
        else
            echo "DIFF $base"
        fi
    else
        echo "MISSING $base (not in /usr/local/bin)"
    fi
done
```

---

## Key Rules (never break)

1. Never change OpenClaw `network_mode` away from `host`
2. Tunnel must have `ServerAliveInterval=10`
3. Nginx changes require `nginx -t` test before reload
4. No external ports open except 22, 80, 443
5. `YOUR-PROJECT` is the source of truth — live scripts must match repo or be flagged
6. **Claude Code is standalone** — direct to api.anthropic.com, no proxy (see GOLDEN_RULES.md Rule 13)

---

## Claude Code Architecture (updated 2026-05-30)

**Rule 13 — non-negotiable.** Claude Code connects directly to `api.anthropic.com`. No proxy. No ANTHROPIC_BASE_URL override.

```
claude      → api.anthropic.com (direct HTTPS, Pro OAuth)    ← ALWAYS use this
jeanne-code → VenzariAI Router :4001 (SSH tunnel) → jeanne-primary:latest (Ollama)  ← rate-limited fallback
OpenClaw    → VenzariAI Router :4001 (SSH tunnel) → Ollama / cloud APIs
```

### Using jeanne-code (local model fallback — Plan B, approved 2026-05-30)

```bash
# When Anthropic rate limits hit:
jeanne-code                              # starts Claude Code via VenzariAI Router
# Inside jeanne-code session:
/model claude-haiku-4-5-20251001        # routes to jeanne-primary:latest on Ollama
# To go back: exit and use 'claude' normally
```

Safe by design: env vars scoped to subprocess only. If VenzariAI Router tunnel is down, falls back to `claude` automatically.

### Clean-state verification

```bash
bash /usr/local/bin/jeanne-bootstrap-check   # full 6-check health validator
# Or manually:
env | grep "^ANTHROPIC" && echo "BAD: overrides present" || echo "OK"
type claude  # must show binary path, not "function"
```

See `docs/claude-code-rollback.md` for incident history. See `docs/plans/claude-code-local-fallback-plan.md` for jeanne-code rationale.

---

## GitHub-First Principle (Rule 16)

Before building any new script, service, or feature in this layer: **search GitHub for existing implementations.**

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load github-search
# Then follow agents/skills/github-search/SKILL.md protocol
```

Copy code structure in most cases. Security audit before committing:
```bash
bash /opt/YOUR-PROJECT/ops/security/github-import-audit.sh /tmp/<cloned-repo>
```


---

## [YOUR-AI-NAME]-DASHBOARD-V8 ([your-vps-address]

**Deployed:** 2026-05-31 | **Status:** LIVE — primary dashboard at [your-domain.com]

| What | Value |
|---|---|
| Path | `/opt/[YOUR-AI-NAME]-DASHBOARD-V8` |
| URL | `https://[your-domain.com]` (nginx proxy :5010) |
| Systemd | `jeanne-dashboard-v8.service` |
| DB | `venzarai_hub` PostgreSQL (127.0.0.1:5432) |
| Login | [your-email] / Jeanne2026! |

### V8 Operations

```bash
# Redeploy
cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8
git pull && npm run build
php artisan config:cache && php artisan route:cache
sudo systemctl restart jeanne-dashboard-v8

# Check status
systemctl status jeanne-dashboard-v8
curl http://127.0.0.1:5010/

# Run migrations
php artisan migrate --force

# Domain swap (future)
# Edit .env: APP_NAME="New Name", APP_URL=https://newdomain.com, SESSION_DOMAIN=newdomain.com
# Then: php artisan config:cache && sudo systemctl restart jeanne-dashboard-v8
```

### V8 vs V5

| | V5 (legacy) | V8 (current) |
|---|---|---|
| Stack | Flask/Jinja2/Vuetify | Laravel/React/Inertia |
| Port | :5002 | :5010 |
| URL | [your-domain.com]/v5 | [your-domain.com] |
| DB | readykit (PostgreSQL) | venzarai_hub (PostgreSQL) |
| Auth | Flask-Security | Laravel Breeze + Spatie RBAC |
