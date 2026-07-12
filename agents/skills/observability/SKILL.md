---
name: observability
description: |
  Review logs, RAM, disk, and container health. Use when diagnosing system issues or verifying system health. Covers docker logs, systemd status, RAM usage, disk space, and process monitoring on both VPS.
version: "2.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Observability — Logs, RAM, Disk, Grafana

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Check system health (RAM, disk, logs, Grafana) before declaring any incident resolved or any service healthy.

---

### When to Use

- Before and after any infrastructure change on either VPS
- When a service is reported as slow, timing out, or unresponsive
- As first step in any debugging session
- When `check-all.sh` reports a failure
- When RAM or disk alerts fire on the Venzari VPS

---

---

## Detail

### Process

1. **Read CONTEXT.md first.**
   Confirm VPS identity. Venzari VPS (158.220.105.107) runs the AI stack. Venzari VPS (127.0.0.1) runs OpenClaw only.

2. **Check RAM on Venzari VPS.**
   ```bash
   "free -h && echo '---' && cat /proc/meminfo | grep -E 'MemAvailable|SwapUsed'"
   ```
   RAM < 2 GB available = performance cliff. Swap in use = containers thrashing. Escalate immediately.

3. **Check disk on Venzari VPS.**
   ```bash
   "df -h / /opt /var && du -sh /var/lib/docker 2>/dev/null | head -5"
   ```
   If `/` is > 85% full, do not proceed with any build operation. Prune first:
   `"docker system prune -f"` (never: `docker system prune -af` — removes all images).

4. **Check container status.**
   ```bash
   "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
   ```
   All expected containers must show `Up`. Any `Exited` or `Restarting` is an incident.

5. **Check logs for errors (last 50 lines per critical container).**
   ```bash
   "docker logs venzarai-router --tail 50 2>&1 | grep -i 'error\|exception\|traceback'"
   "docker logs chromadb --tail 20 2>&1"
   ```
   On Venzari VPS:
   ```bash
   docker logs jeannebrain-openclaw-v5 --tail 50 2>&1 | grep -i 'error\|timeout\|refused'
   ```

6. **Check Grafana if accessible.**
   Grafana runs on Venzari VPS port 3001 (internal). Access via SSH tunnel if set up.
   Look for: CPU > 80% sustained, RAM < 2 GB available, disk write saturation.
   If Grafana is not accessible, use `vmstat 1 5` and `iostat -x 1 3` from ssh.

7. **Check recent log files (non-Docker services).**
   ```bash
   "journalctl -n 50 --no-pager -p err"
   ```

8. **Record the health baseline.**
   Document: RAM available, disk%, all container statuses, any log errors found.
   This becomes the before-state for any subsequent change.

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "The service looks fine from the outside." | Swap usage and log errors are invisible from curl. Check RAM explicitly. |
| "Grafana isn't accessible, so I'll skip this step." | Use `free -h` and `docker logs` — equivalent information without Grafana. |
| "It's probably just a temporary spike." | Show the `free -h` output. "Probably" is not a measurement. |
| "I checked RAM yesterday and it was fine." | Memory leaks and container restarts change RAM usage hourly. Check now. |
| "The disk usage warning doesn't affect the current task." | A full disk during a `docker build` causes cryptic failures mid-layer. Check disk before every build. |
| "Logs look clean." | Show the grep output — even if it's empty, paste `(no errors found)` explicitly. |

---

### Red Flags

Stop immediately and escalate to Billy if:

- RAM available < 2 GB on Venzari VPS (swap usage > 0 is a strong indicator).
- Disk on `/` > 90% — do not attempt any build, rebuild, or git operation.
- Any container that was `Up` is now `Exited` after your investigation step (investigation caused a cascade).
- VenzariAI Router logs show repeated `CUDA out of memory` or `OOM killer` traces.
- `docker logs chromadb` shows `SIGTERM received` — ChromaDB was killed by OOM, restart required and memory root-cause must be found.
- Three consecutive `docker logs` reads show the same crash loop (same stack trace, < 60s between crashes).

---

### Verification

Observability check is complete when all of the following are documented:

```
# RAM (show actual output)
free -h
# Expected: "available" column > 2.0G

# Disk (show actual output)
df -h /
# Expected: Use% < 85%

# Containers (show actual output)
docker ps -a --format "table {{.Names}}\t{{.Status}}"
# Expected: all expected containers show "Up"

# Logs (show actual grep output or explicit "(no errors found)")
docker logs <container> --tail 50 2>&1 | grep -i "error|exception"
```

---

## Reference

### Forbidden Actions

| Action | Rule | Why |
|---|---|---|
| Skip SSOT commit | Rule 11 | Infrastructure must be in YOUR-PROJECT first |
| `docker restart` healthy container | Rule 1 | edit→rebuild→verify instead |
| `ANTHROPIC_BASE_URL` system-wide | Rule 13 | Breaks Claude Code OAuth |
| `liveTurnTimeoutMs` in openclaw.json | Rule 6 | Caused 2-day crash loop |

### Doc Impact

| Doc | What to update |
|---|---|
| `system-map/CURRENT_STATE.md` | Update service status if changed |

