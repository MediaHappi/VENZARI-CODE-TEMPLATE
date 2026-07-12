---
doc_type: runbook
last_updated: 2026-07-06
ssot_status: CURRENT
audience: all-agents
---

# Runbook: Monitoring Issues

**Layer:** 05-monitoring  
**Full runbook:** `05-monitoring/RUNBOOK.md`  
**Last updated:** 2026-05-30

---

## Quick Reference

| Problem | Jump to |
|---|---|
| Grafana not accessible | `05-monitoring/RUNBOOK.md` → Grafana section |
| Loki missing logs | `05-monitoring/RUNBOOK.md` → Loki section |
| Promtail not shipping logs | `05-monitoring/RUNBOOK.md` → Promtail section |
| Alert firing falsely | `05-monitoring/RUNBOOK.md` → Alerts section |
| RAM > 80% on Venzari VPS | `05-monitoring/RUNBOOK.md` → RAM section |

---

## Accessing Grafana (Internal Only)

```bash
# SSH tunnel from your local machine:
ssh -L 3001:127.0.0.1:3001 venzari-vps-billy
# Then open: http://localhost:3001
```

## Stack Status Check

```bash
ssh venzari-vps-billy "docker ps | grep -E 'grafana|loki|promtail'"
# Expected: all 3 containers Up
```

## Most Common: Promtail Not Shipping

```bash
ssh venzari-vps-billy "docker logs promtail --tail 30 2>&1 | grep -E 'error|Error|level=error'"

# Restart Promtail
ssh venzari-vps-billy "docker restart promtail && sleep 5 && docker logs promtail --tail 10"
```

## RAM Monitor

```bash
ssh venzari-vps-billy "free -h"
# Target: > 2GB free

# If low — check which models are loaded
ssh venzari-vps-billy "curl -s http://127.0.0.1:11434/api/ps | python3 -m json.tool"

# Run container memory audit to find the culprit
ssh venzari-vps-billy "bash /usr/local/bin/container-memory-audit.sh" 2>/dev/null

# Current memory limits (B5 audit, 2026-05-30):
# jeanne-dashboard-v8-web-1: 512MB (raised from 256MB)
# jeanne-dashboard-v8-worker-1: 512MB (raised from 256MB)
# acelle_db: 768MB (raised from 512MB)
```

## Inference Monitoring (inference-monitor.sh)

`inference-monitor.sh` runs every 5 minutes (cron) on Venzari VPS and collects 10 inference
metrics. Deployed as task D8 (0380).

```bash
# Check inference-monitor status
ssh venzari-vps-billy "tail -20 /var/log/jeanne/inference-monitor.log" 2>/dev/null

# Check if cron is running inference-monitor
ssh venzari-vps-billy "crontab -l | grep inference-monitor"

# Manual run
ssh venzari-vps-billy "bash /usr/local/bin/inference-monitor.sh" 2>/dev/null
```

## Container Memory Audit (container-memory-audit.sh)

`container-memory-audit.sh` scans actual RSS vs allocated limits and flags OOM risks.
Deployed as task B5 (0375).

```bash
# Run container memory audit
ssh venzari-vps-billy "bash /usr/local/bin/container-memory-audit.sh" 2>/dev/null

# Check audit log
ssh venzari-vps-billy "tail -30 /var/log/jeanne/container-memory-audit.log" 2>/dev/null
```

The audit flags any container where actual usage exceeds 80% of its memory limit, and
recommends a safe new limit (actual_usage * 1.5 rounded to nearest 128MB).

This script also runs as part of smoke-test.sh (check #11) after any docker update --memory operation.

**Full runbook with all procedures:** `05-monitoring/RUNBOOK.md`
