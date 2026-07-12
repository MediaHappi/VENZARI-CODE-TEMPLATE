---
name: infra
description: |
  General infrastructure operations skill for Venzari VPS and Venzari VPS. Use for ad-hoc infrastructure tasks not covered by more specific skills. Covers Docker, systemd, SSH, nginx, cron.
version: "2.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read, Write, Edit
---

# Skill: Infrastructure Operations

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Safely inspect and modify [YOUR-AI-NAME] infrastructure (SSH, tunnel, containers, cron) with the discipline of check-before-touch and verify-after-every-change.

---

### When to Use

- Any task touching Docker containers on Venzari VPS or Venzari VPS
- Any task modifying SSH tunnel configuration
- Any task adding, removing, or changing cron entries
- Any task that requires verifying a service is actually running (not just "should be")

---

---

## Detail

### Process

0. **[MANDATORY for script/config changes] Run codegraph check before touching any script or config.**
   ```bash
   # Check if the script or config is referenced by other code
   python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py context "<script or config name>"

   # If changing a function in a script, check blast radius
   python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py impact "<function_name>"
   ```
   Skip only for pure container restarts or health checks that touch no files. Any edit to
   a .sh, .py, .yaml, or .json configuration file requires this check first.

1. **Read CONTEXT.md before touching anything.**
   Confirm which VPS you are on (Brain: 127.0.0.1, Memory: 158.220.105.107).
   Confirm the exact service name and port from the Key Ports table.

2. **Establish baseline state.**
   Run `docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"` and record the output.
   This is your before-state. Never make changes without a recorded before-state.

3. **Check logs before touching config.**
   `docker logs <container_name> --tail 50` or `journalctl -u <service> -n 50`.
   Identify the actual error before deciding on a fix.

4. **Backup before editing any config.**
   `cp /path/to/config /path/to/config.bak.$(date +%Y%m%d-%H%M%S)`
   No backup = no edit. Non-negotiable.

5. **Make exactly one change at a time.**
   Edit the source file (never patch a running container).
   Describe the single change in one sentence before making it.

6. **Rebuild and restart the affected service only.**
   For Docker: `docker compose up -d --build <service_name>` — not `docker compose up -d` (avoids restarting unrelated services).
   For systemd: `systemctl restart <service_name>` — not reload unless explicitly appropriate.

7. **Wait for the service to reach running state.**
   `docker ps` must show `Up X seconds (healthy)` or `Up X seconds` — not `Restarting` or `Exited`.
   Wait up to 30 seconds. If not up in 30 seconds, read logs before proceeding.

8. **Verify the endpoint responds.**
   Show the actual HTTP status code. For VenzariAI Router: `curl -s -o /dev/null -w "%{http_code}" http://localhost:4001/health/liveliness`
   For other services: use the appropriate health endpoint from CONTEXT.md.

9. **Confirm no regression on adjacent services.**
   Re-run `docker ps` and confirm all previously-running containers are still running.
   If any container that was `Up` before is now `Exited`, treat this as an incident.

10. **Record outcome.**
    Write the after-state (docker ps output + curl response) to the task's evidence field.

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "I restarted it, so it should be fine now." | Show `docker ps` output showing the container status. "Restarted" is not the same as "running and healthy." |
| "The config looks right." | Config correctness is not service health. Show the endpoint response. |
| "It was working before, so this change can't have broken it." | Show the after-state. Confirmation bias is not evidence. |
| "I'll skip the backup — it's just a small change." | Every config backup takes 3 seconds. An unrecoverable config takes hours. Back it up. |
| "I'll restart all the containers to be sure." | Restarting all containers is not precision. It risks disrupting VenzariAI Router during inference (GOLDEN RULE 17). Restart only the affected service. |
| "The logs say nothing, so there's no problem." | Empty logs can mean the container is not logging or the crash happened before logging started. Check `docker inspect` for exit codes. |
| "It's probably just slow to start." | "Probably" is not a state. Wait 30 seconds, then check logs. Name the actual state. |
| "I'll just `kill -9` the stuck runner process, that's faster than a container restart." | Confirmed live (task I0000000077, 2026-07-03): killing an Ollama model-runner PID directly bypasses Ollama's own unload bookkeeping. `/api/ps` kept reporting the model as loaded/pinned (`expires_at` far in the future) with no matching OS process, and subsequent requests hung indefinitely waiting on a scheduler slot for a process that no longer existed. Use `docker restart <container>` (or Ollama's own unload API, `POST /api/generate {"keep_alive":0}`) instead — never `kill -9` a runner PID directly. |

---

### Red Flags

Stop immediately and escalate to Billy if:

- A container that was previously `Up` is now `Exited` after your change and does not recover in 60 seconds.
- `docker logs` shows `ECONNRESET` or `Connection refused` on a service that was previously healthy.
- You have made the same change three times and the service is still not responding correctly (GOLDEN RULE 8: three identical failures = escalate).
- VenzariAI Router shows `unhealthy` in `docker ps` — this is a false positive during long Ollama inference. Do NOT restart it (GOLDEN RULE 17/23).
- The SSH tunnel `ServerAliveInterval` has been changed to a value > 10 — revert immediately.
- Any config edit has introduced `liveTurnTimeoutMs` into openclaw.json — remove it immediately.

---

### Verification

Completion requires all of the following — prose descriptions do not count:

```
# 1. Container status (show actual output)
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
# Expected: all previously-running containers show "Up", no "Exited" or "Restarting"

# 2. Endpoint health check (show HTTP status)
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:<PORT>/health
# Expected: HTTP 200

# 3. No regression on adjacent services
# Show before-state and after-state side by side (container names + statuses)
```

If the task involved a cron change:
```
crontab -l | grep <script_name>
# Expected: entry is present exactly once (not duplicated)
```

### Network Diagnostics (Rule 1 applies — host tools, not docker exec for fixes)

Since OpenClaw uses `network_mode: host`, diagnose from the Venzari VPS host:
```bash
ss -tulpn                         # all listening ports (sees OpenClaw :18789)
netstat -tulpn | grep 18789       # OpenClaw port specifically
iptables -L -n --line-numbers     # firewall rules
```
Network tools installed on Venzari VPS and Venzari VPS hosts: net-tools, iproute2, iptables.

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

