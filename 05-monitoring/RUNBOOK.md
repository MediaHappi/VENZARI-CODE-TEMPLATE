# Layer 05 — Monitoring Runbook

**Last updated:** 2026-05-30 10:30 UTC | **Task:** 0306
**Layer stability:** FLEXIBLE
**Domain:** Grafana, Loki, Promtail, backups, alerts, RAM monitoring

---

## Monitoring Stack Overview

All monitoring containers run on [your-vps-address]

| Service | Container | Internal Port | Access |
|---|---|---|---|
| Promtail | `promtail` | internal | Log collector, no direct UI |
| Loki | `loki` | 3100 | Log storage, internal API |
| Grafana | `grafana` | 3001 | Dashboards, SSH tunnel required |

---

## Accessing Grafana

Grafana is internal-only. Access via SSH tunnel:

```bash
# On your local machine:
ssh -L 3001:127.0.0.1:3001 venzari-vps-billy
# Then open: http://localhost:3001
```

Or directly on [your-vps-address]
```bash
ssh venzari-vps-billy "curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/ && echo ' GRAFANA OK'"
```

### Restart Grafana
```bash
ssh venzari-vps-billy "docker restart grafana && sleep 3 && curl -sf http://127.0.0.1:3001/api/health"
```

---

## Loki (Log Storage)

### Health check
```bash
ssh venzari-vps-billy "curl -sf http://127.0.0.1:3100/ready && echo ' LOKI OK'"
```

### Query recent logs (via Loki API)
```bash
# Query last 20 log lines for all jeanne jobs
ssh venzari-vps-billy "curl -s 'http://127.0.0.1:3100/loki/api/v1/query_range?query={job=\"jeanne\"}&limit=20&start=$(date -d '1 hour ago' +%s)000000000&end=$(date +%s)000000000' | python3 -m json.tool | head -60"

# Query errors only
ssh venzari-vps-billy "curl -s 'http://127.0.0.1:3100/loki/api/v1/query_range?query={job=\"jeanne\"}|=\"ERROR\"&limit=20&start=$(date -d '1 hour ago' +%s)000000000&end=$(date +%s)000000000' | python3 -m json.tool | head -40"
```

### Grafana Loki query (LogQL — use in Explore tab)
```logql
# All jeanne logs, last 1 hour
{job="jeanne"} | limit 100

# Errors only
{job="jeanne"} |= "ERROR" | limit 50

# VenzariAI Router request logs
{job="venzarai-router"} | limit 50

# OpenClaw logs
{container="jeannebrain-openclaw-v5"} | limit 50
```

### Restart Loki
```bash
ssh venzari-vps-billy "docker restart loki"
```

---

## Promtail (Log Collector)

Promtail ships logs from log files to Loki.

### Status check
```bash
ssh venzari-vps-billy "docker ps | grep promtail && docker logs promtail --tail 10"
```

### Restart Promtail
```bash
ssh venzari-vps-billy "docker restart promtail"
```

---

## Log File Locations

### [your-vps-address]
```
/home/billy/.openclaw/logs/
  ├── context-injector.log       ← context injector (every 2min)
  ├── post_response_sync.log     ← vector store sync (every 5min)
  ├── healthcheck.log            ← jeanne-healthcheck.sh (every 5min)
  ├── ram-monitor.log            ← RAM monitor (every 10min)
  ├── venzarai-router-patch.log          ← VenzariAI Router RAM patch (hourly)
  ├── jeanne-cto-sync.log        ← repo sync (every 15min)
  ├── hubspot_sync.log           ← HubSpot sync (daily 9am)
  └── proposals-gate.log         ← proposals gate (daily 8:15am)
```

### [your-vps-address]
```
/var/log/jeanne-*.log            ← platform service logs
/home/billy/jeanne-backups/      ← backup archives + logs
```

---

## Daily Health Check Procedure

Run this every morning or after any incident. Expected time: ~3 minutes.

```bash
# 1. Run the unified health check script
/opt/YOUR-PROJECT/ops/monitoring/check-all.sh
# Exit 0 = all healthy. Exit 1 = investigate.

# 2. Check RAM on both VPS
ssh venzari-vps-billy "free -h | grep Mem"
free -h | grep Mem
# Target: > 2GB free on each

# 3. Check disk on [your-vps-address]
ssh venzari-vps-billy "df -h / | tail -1"
# Target: < 80% used

# 4. Verify Grafana is reachable
ssh venzari-vps-billy "curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/api/health"
# Expected: 200

# 5. Verify Loki is ready
ssh venzari-vps-billy "curl -sf http://127.0.0.1:3100/ready && echo ' OK'"

# 6. Confirm backup ran overnight
ssh venzari-vps-billy "ls -lt /home/billy/jeanne-backups/ | head -5"
# Most recent file should be < 24h old

# 7. Check for recent errors in container logs
ssh venzari-vps-billy "docker logs jeanne-dashboard-v8-web-1 --tail 20 --since 12h 2>&1 | grep -i error | head -10"

# 8. Confirm OpenClaw is healthy ([your-vps-address]
curl -sf http://127.0.0.1:9000/health 2>/dev/null || echo "CHECK: openclaw health endpoint"
```

---

## RAM Monitor

`jeanne-ram-monitor.sh` runs every 10 minutes on [your-vps-address]

- **Alert threshold:** < 2GB free RAM on [your-vps-address]
- **Alert method:** Telegram message to Billy
- **Log:** `/home/billy/.openclaw/logs/ram-monitor.log`

### Check RAM manually
```bash
ssh venzari-vps-billy "free -h"
# Target: > 2GB free at all times
```

### RAM usage targets
| VPS | Total RAM | Target free |
|---|---|---|
| [your-vps-address]
| [your-vps-address]

High memory consumers on [your-vps-address]
- `ollama` with `jeanne-primary:latest` loaded: ~2.5 GB
- `ollama` with `jeanne-primary-coder:7b` loaded: ~5.5 GB (DO NOT load simultaneously with jeanne-primary)
- `venzarai-router`: ~500 MB
- `chromadb`: ~300 MB
- `jeanne-dashboard-v8-web-1`: ~400 MB

---

## Alert Thresholds

| Condition | Threshold | Action |
|---|---|---|
| Response time | > 5s for 5 min | Telegram alert |
| Error rate | > 5% for 10 min | Critical alert |
| Disk usage | > 80% | Warning alert |
| SSH tunnel down | > 60s | Critical + systemd restart |
| RAM free | < 2 GB | Telegram alert |

---

## Watchdog

`jeanne-watchdog.sh` runs every 2 minutes on [your-vps-address]

- Checks SSH tunnel health (venzarai-tunnel.service)
- Restarts tunnel if down
- **Log:** check via `journalctl` or cron output

### Manual watchdog run
```bash
/usr/local/bin/jeanne-watchdog.sh
```

---

## ChromaDB Health Checks (Updated 2026-07-04, task L0000000004)

**IMPORTANT:** ChromaDB v1 API is deprecated. All health checks MUST use v2 endpoints.

### Health check endpoint
```bash
# ChromaDB v2 heartbeat (venzari-vps-billy)
curl -s http://127.0.0.1:8001/api/v2/heartbeat

# Expected response:
# {"nanosecond heartbeat":1783126396479324729}
# HTTP 200

# If you see HTTP 410 with "deprecated" error, v1 endpoint was used — UPDATE THE SCRIPT
```

### Status check
```bash
ssh venzari-vps-billy "curl -sf http://127.0.0.1:8001/api/v2/heartbeat && echo ' ChromaDB v2 OK' || echo ' FAIL'"
```

### Restart ChromaDB
```bash
ssh venzari-vps-billy "docker restart chromadb && sleep 3 && curl -sf http://127.0.0.1:8001/api/v2/heartbeat"
```

### Health check script integration
All monitoring scripts (health-check.sh, daily_health_check.sh, check-all.sh) already use v2 endpoints:
- Location: `/opt/YOUR-PROJECT/ops/scripts/health-check.sh` (line 8001/v2 reference)
- Location: `/opt/YOUR-PROJECT/ops/monitoring/health-check.sh`

**Verify no v1 endpoints remain:**
```bash
grep -r "8001/api/v1/heartbeat" /opt/YOUR-PROJECT/ops --include="*.sh"
# Should return: (no matches)
```

---

## Backup Inventory

| Backup | Schedule | Location | Retention |
|---|---|---|---|
| PostgreSQL dump | Daily 3am (Brain cron) | `/home/billy/jeanne-backups/` | 30 days |
| Full platform backup | Daily 2am | `/home/billy/jeanne-backups/` | 30 days |
| ChromaDB backup | Weekly | `/home/billy/jeanne-backups/` | — |
| Acelle MySQL | Daily 4am | `/home/billy/jeanne-backups/` | 30 days |
| VenzariAI Router config backup | On change | `/opt/venzarai-router/venzarai-router_config.yaml.bak.*` | Manual |
| OpenClaw config backup | On change | `/home/billy/.openclaw/openclaw.json.bak.*` | Manual |

### Check backup freshness
```bash
ssh venzari-vps-billy "ls -lt /home/billy/jeanne-backups/ | head -10"
```

---

## Platform Health Script

A single-command health check script is at:
```
/opt/YOUR-PROJECT/ops/monitoring/check-all.sh
```

Run it from [your-vps-address]
```bash
/opt/YOUR-PROJECT/ops/monitoring/check-all.sh
# Exit 0 = all healthy
# Exit 1 = one or more services down
```

---

## Common Failures

### Failure: Grafana showing no data

**Problem:** Grafana dashboards show "No data" or blank panels.

**Diagnosis:**
```bash
# 1. Is Loki healthy?
ssh venzari-vps-billy "curl -sf http://127.0.0.1:3100/ready && echo LOKI_OK"
# 2. Is Promtail shipping?
ssh venzari-vps-billy "docker logs promtail --tail 20 | grep -i 'error\|warn\|sent'"
# 3. Check Grafana data source connectivity (in UI: Configuration → Data Sources → Loki → Test)
```

**Root Causes:**
- Loki container restarted and Promtail hasn't reconnected
- Grafana time range set to a period before Promtail was running
- Loki disk full or OOM-killed

**Resolution:**
```bash
# Restart stack in correct order: promtail → loki → grafana
ssh venzari-vps-billy "docker restart promtail && sleep 5 && docker restart loki && sleep 5 && docker restart grafana"
```

**Verify:**
```bash
ssh venzari-vps-billy "curl -sf http://127.0.0.1:3100/ready && echo LOKI_OK"
ssh venzari-vps-billy "curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/api/health"
```

**Rollback:** No state change — restart is idempotent.

---

### Failure: RAM monitor is spamming Telegram

**Problem:** Repeated RAM alerts arriving via Telegram.

**Diagnosis:**
```bash
# What is using RAM?
ssh venzari-vps-billy "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}' | sort -k2 -rh | head -10"
# What models does Ollama have loaded?
ssh venzari-vps-billy "curl -s http://127.0.0.1:11434/api/ps | python3 -m json.tool"
```

**Root Causes:**
- `jeanne-primary-coder:7b` loaded simultaneously with `jeanne-primary:latest` (combined ~8GB)
- Memory leak in a long-running container

**Resolution:**
```bash
# Unload coder model immediately:
ssh venzari-vps-billy "curl -X POST http://127.0.0.1:11434/api/generate -d '{\"model\":\"jeanne-primary-coder:7b\",\"keep_alive\":0}'"
# If still critical, restart non-essential containers:
ssh venzari-vps-billy "docker restart chromadb"
```

**Verify:**
```bash
ssh venzari-vps-billy "free -h | grep Mem"
# Must show > 2GB free before considering resolved
```

**Rollback:** N/A — no config changed.

---

### Failure: Disk > 80%

**Problem:** Disk usage alert on [your-vps-address]

**Diagnosis:**
```bash
ssh venzari-vps-billy "df -h / | tail -1"
# Find largest consumers:
ssh venzari-vps-billy "du -sh /home/billy/jeanne-backups/* | sort -rh | head -10"
ssh venzari-vps-billy "du -sh /usr/share/ollama/.ollama/models/blobs/* | sort -rh | head -5"
```

**Root Causes:**
- Old backup archives not rotated
- Unused Ollama model blobs accumulating
- `/tmp` left with large backup staging directories

**Resolution:**
```bash
# Run cleanup script:
ssh venzari-vps-billy "/usr/local/bin/jeanne-cleanup.sh"
# Manual: remove backups older than 30 days
ssh venzari-vps-billy "find /home/billy/jeanne-backups/ -mtime +30 -delete"
# Clean /tmp backup staging:
ssh venzari-vps-billy "rm -rf /tmp/jeanne-backup-*"
```

**Verify:**
```bash
ssh venzari-vps-billy "df -h / | tail -1"
# Target: < 80% used
```

**Rollback:** N/A — cleanup is safe.

---

## Grafana Dashboards

Access: SSH tunnel → localhost:3001 (Grafana on [your-vps-address]

| Dashboard | Purpose |
|---|---|
| [YOUR-AI-NAME] Agent Performance | VenzariAI Router request latency, model hit rates, token usage |
| Training Pipeline | Fine-tune job status, dataset size, model version history |
| Infrastructure | CPU/RAM/disk for Brain + [your-vps-address]
| Memory Layer | ChromaDB query latency, PostgreSQL connections, Redis hit rate |
| Acelle / HubSpot Sync | Email delivery rates, sync lag, bounce rates |

---

## Alert Thresholds

| Alert | Threshold | Action |
|---|---|---|
| Response time | >5 seconds P95 | Telegram alert → check Ollama loaded |
| Error rate | >5% | Telegram alert → check VenzariAI Router logs |
| Training job fails | 2 consecutive failures | Telegram alert → check RunPod credits |
| Disk usage | >80% | Telegram alert → clean /tmp and old GGUFs |
| SSH tunnel down | >60 seconds | Auto-restart via watchdog service |
| OpenClaw offline | >30 seconds | Telegram alert (external monitor) |

All alerts route to Billy via Telegram (Grafana → n8n → Telegram).

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

## Grafana Alerting Status (verified 2026-05-30)

Grafana alerting provisioning config exists at `/etc/grafana/provisioning/alerting/` in the container.

### Current Alert Channels
- Alerting config is provisioned but **Telegram contact point is NOT verified as active**.
- To check: `ssh venzari-vps-billy "curl -s -u admin:admin http://127.0.0.1:3001/api/v1/provisioning/contact-points"`
- To add Telegram alerts: Grafana UI → Alerting → Contact Points → Add Telegram webhook

### Recommended RAM alert (if not set)
```bash
# Add alert: RAM < 1GB free on [your-vps-address]
# Threshold: node_memory_MemAvailable_bytes < 1073741824
# Contact point: Telegram (configure in Grafana UI)
```

### Alternative — jeanne-ram-monitor.sh
The platform uses `jeanne-ram-monitor.sh` cron (every 10min) for RAM alerting via Telegram.
This is the **active alerting path** — Grafana alerts are supplemental.

---

## Log Queries from [your-vps-address]

### Tail live logs (docker)
```bash
# OpenClaw logs ([your-vps-address]
docker logs jeannebrain-openclaw-v5 --tail 50 -f

# VenzariAI Router logs ([your-vps-address]
ssh venzari-vps-billy "docker logs venzarai-router --tail 50 -f"

# Ollama logs
ssh venzari-vps-billy "docker logs ollama --tail 50"

# Dashboard logs
ssh venzari-vps-billy "docker logs jeanne-dashboard-v8-web-1 --tail 50"
```

### Query Loki from [your-vps-address]
```bash
# Recent errors (last 1 hour)
ssh venzari-vps-billy "curl -s 'http://127.0.0.1:3100/loki/api/v1/query_range?query={container_name=~\".+\"}|=\"ERROR\"&limit=20&start=\$(date -d \"1 hour ago\" +%s)000000000&end=\$(date +%s)000000000' | python3 -c 'import sys,json; d=json.load(sys.stdin); [print(v[1]) for r in d.get(\"data\",{}).get(\"result\",[]) for v in r[\"values\"]]' 2>/dev/null | head -30"

# All jeanne service logs (last 30 min)
ssh venzari-vps-billy "curl -s 'http://127.0.0.1:3100/loki/api/v1/query_range?query={job=~\"jeanne.*\"}&limit=50&start=\$(date -d \"30 min ago\" +%s)000000000&end=\$(date +%s)000000000'"
```
