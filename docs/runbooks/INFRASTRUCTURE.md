---
doc_type: runbook
last_updated: 2026-07-06
ssot_status: CURRENT
audience: all-agents
---

# Runbook: Infrastructure Issues

**Layer:** 00-foundation  
**Full runbook:** `00-foundation/RUNBOOK.md`  
**Last updated:** 2026-05-28

---

## Quick Reference

| Problem | Jump to |
|---|---|
| SSH tunnel down (VenzariAI Router/Ollama unreachable) | `00-foundation/RUNBOOK.md` → SSH Tunnel section |
| Venzari VPS OpenClaw container not responding | `00-foundation/RUNBOOK.md` → OpenClaw section |
| Nginx returning 502/504 | `00-foundation/RUNBOOK.md` → Nginx section |
| YOUR-PROJECT sync not running | `00-foundation/RUNBOOK.md` → Sync section |
| Venzari VPS disk full | `00-foundation/RUNBOOK.md` → Disk section |
| Cron job not firing | `00-foundation/RUNBOOK.md` → Cron section |

---

## Most Common: SSH Tunnel Down

```bash
# Check tunnel status on Venzari VPS
systemctl status venzarai-tunnel.service
systemctl status ollama-tunnel.service

# Restart (watchdog should auto-restart, but manual if needed)
systemctl restart venzarai-tunnel.service
systemctl restart ollama-tunnel.service

# Verify VenzariAI Router reachable after restart
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:4001/health/liveliness
# Expected: HTTP 200
```

## Most Common: Nginx 502/504

```bash
# Check which upstream is failing
sudo nginx -t && sudo nginx -s reload

# Check upstream services
ssh venzari-vps-billy "docker ps | grep -E 'web|dashboard'"
curl -s http://localhost:5002/health  # dashboard

# Check Nginx error log
sudo tail -50 /var/log/nginx/error.log | grep -E "502|504|upstream"
```

## Key Paths

| What | Venzari VPS | Venzari VPS |
|---|---|---|
| OpenClaw config | /home/billy/.openclaw/openclaw.json | — |
| Nginx config | /etc/nginx/sites-enabled/[your-domain.com] | — |
| Systemd units | /etc/systemd/system/venzarai-tunnel.service | — |
| Ops scripts (live) | /usr/local/bin/ | /usr/local/bin/ |
| Ops scripts (repo) | /opt/YOUR-PROJECT/ops/venzari-vps/scripts/ | /opt/YOUR-PROJECT/ops/venzari-vps/ |

**Full runbook with all procedures:** `00-foundation/RUNBOOK.md`  
**VPS topology:** `system-map/vps-topology.md`
