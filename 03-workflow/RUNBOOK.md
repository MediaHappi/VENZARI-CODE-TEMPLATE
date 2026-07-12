# Layer 03 — Workflow Runbook

**Last updated:** 2026-05-30 10:30 UTC
**Layer stability:** FLEXIBLE
**Domain:** n8n, Acelle, HubSpot, AI Content Engine

---

## Service Overview

| Service | Container | Internal Port | Access URL |
|---|---|---|---|
| n8n | `n8n` | 5678 | `[your-domain.com]/n8n` (via nginx proxy) |
| Acelle | `acelle_app` | 8080 | `mail.[your-domain.com]` (via nginx proxy) |
| Acelle DB | `acelle_db` | internal | MySQL, internal only |
| AI Content Engine API | `ai-content-engine-api` | 5001 | `http://127.0.0.1:5001` |
| AI Content Engine Worker | `ai-content-engine-worker` | internal | Background worker |

All containers run on [your-vps-address]

---

## n8n

### Status check
```bash
ssh venzari-vps-billy "docker ps | grep n8n"
ssh venzari-vps-billy "curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:5678/ && echo ' n8n OK'"
```

### External check
```bash
curl -sf -o /dev/null -w "%{http_code}" https://[your-domain.com]/n8n/
# Expected: 200
```

### Restart n8n
```bash
ssh venzari-vps-billy "cd /opt/n8n && docker compose restart"
# n8n compose file: /opt/n8n/docker-compose.yml
```

### Check logs
```bash
ssh venzari-vps-billy "docker logs n8n --tail 30"
```

**WARNING:** n8n has stopped silently twice without logging or alerting. Always check it in every incident diagnostic. Ensure `restart: unless-stopped` is set in `/opt/n8n/docker-compose.yml`.

### Active workflows

Verified 2026-05-27 via `docker exec n8n n8n list:workflow`:

| ID | Name | Status |
|---|---|---|
| `LevH9YI4WksTz1qp` | [Your-AI-Name] Multi-Agent Router | Active |
| `a0wSLKh9Q4DwUKA5` | [Your-AI-Name] Daily Content Pipeline | Active |

Log into n8n UI at `[your-domain.com]/n8n` or `n8n.[your-domain.com]` to manage workflows.

### Access URLs

- `https://[your-domain.com]/n8n/` — proxied via [your-domain.com] nginx location block (HTTP 200 verified 2026-05-27)
- `https://n8n.[your-domain.com]/` — dedicated vhost with SSL (HTTP 200 verified 2026-05-27)

Both routes proxy to `http://127.0.0.1:5678` on [your-vps-address]

---

## Acelle Email Marketing

### Status check
```bash
ssh venzari-vps-billy "docker ps | grep acelle"
ssh venzari-vps-billy "curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/ && echo ' ACELLE OK'"
```

### External check
```bash
curl -sf -o /dev/null -w "%{http_code}" https://mail.[your-domain.com]/
# Expected: 200
```

### Restart Acelle
```bash
ssh venzari-vps-billy "cd /opt/acelle && docker compose restart acelle_app"
# Acelle compose file: /opt/acelle/docker-compose.yml
```

### Check logs
```bash
ssh venzari-vps-billy "docker logs acelle_app --tail 30"
```

**WARNING:** acelle_app has stopped silently twice. Ensure `restart: unless-stopped` in `/opt/acelle/docker-compose.yml`.

**CRITICAL binding rule:** acelle_app must bind to `127.0.0.1:8080`, NOT `0.0.0.0:8080`. nginx proxies mail.[your-domain.com] to it. Docker compose must have `127.0.0.1:8080:80`.

---

## AI Content Engine

### Status check
```bash
ssh venzari-vps-billy "docker ps | grep ai-content-engine"
ssh venzari-vps-billy "curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/ && echo ' CONTENT-ENGINE OK'"
```

### Restart
```bash
ssh venzari-vps-billy "docker compose -f /opt/ai-content-engine/docker-compose.yml restart"
# Or find compose location:
ssh venzari-vps-billy "find /opt -name docker-compose.yml 2>/dev/null | xargs grep -l 'ai-content' 2>/dev/null"
```

### Check logs
```bash
ssh venzari-vps-billy "docker logs ai-content-engine-api --tail 30"
ssh venzari-vps-billy "docker logs ai-content-engine-worker --tail 30"
```

---

## Sync Schedules

| Sync | Schedule | How triggered |
|---|---|---|
| HubSpot → Acelle | Hourly | n8n workflow |
| Acelle → HubSpot | Hourly | n8n workflow |
| Social posting | On approval | n8n cron |
| HubSpot → Acelle (cron backup) | Daily 9am | `hubspot_acelle_sync.py` on [your-vps-address]

---

## Common Failures

### Failure: n8n unreachable at [your-domain.com]/n8n

```bash
# 1. Check container
ssh venzari-vps-billy "docker ps | grep n8n"
# 2. If stopped, restart
ssh venzari-vps-billy "cd /opt/n8n && docker compose up -d"
# 3. Check nginx proxy config
cat /etc/nginx/sites-enabled/[your-domain.com] | grep -A5 "location /n8n"
# 4. Verify n8n is listening
ssh venzari-vps-billy "curl -sf http://127.0.0.1:5678/"
```

### Failure: Acelle emails not sending

```bash
# Check Acelle logs
ssh venzari-vps-billy "docker logs acelle_app --tail 50 | grep -i 'error\|mail\|smtp'"
# Check Postfix (mail relay)
ssh venzari-vps-billy "docker ps | grep postfix"
# Check Acelle DB
ssh venzari-vps-billy "docker ps | grep acelle_db"
```

### Failure: HubSpot sync not running

```bash
# Check cron on [your-vps-address]
crontab -l | grep hubspot
# Run manually to test
source /home/billy/.openclaw/.env
python3 /home/billy/scripts/hubspot_acelle_sync.py
```

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

