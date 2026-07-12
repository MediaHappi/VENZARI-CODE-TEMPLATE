---
name: build-and-verify
description: |
  Deploy changes to live infrastructure and verify with real curl commands. Use after every infrastructure change. Shows HTTP status codes — never assumes a fix worked. Covers Venzari VPS and Venzari VPS deploys.
version: "2.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Build and Verify

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Edit source files, rebuild the affected service, and verify it responds correctly via HTTP — never patch running containers and never self-report completion without curl evidence.

---

### When to Use

- Any task that changes Python source, Docker configs, or shell scripts in a running service
- After any config file change that requires a service restart
- Enforces GOLDEN RULE 2: verify with curl, show HTTP status

---

---

## Detail

### Process

0. **[MANDATORY] Run codegraph context and impact analysis before ANY code change.**
   ```bash
   # Understand what the task touches structurally
   python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py context "<task description>"

   # Assess blast radius before editing a specific symbol/function
   python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py impact "<symbol_name>"
   ```
   Do not skip this. It reveals: callers that will break, files that depend on the symbol,
   and related symbols you may need to update. "I know what it does" is not a substitute
   for structural analysis. See `docs/architecture/MEMORY_ARCHITECTURE.md` Layer 4.

1. **Record the before-state.**
   ```bash
   docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```
   Paste this output. Every subsequent verification is compared against it.

2. **Edit source only — never patch running containers.**
   Edit the file in the source directory (e.g., `/opt/jeannebrain/` on Venzari VPS, not inside `docker exec`).
   ```bash
   # CORRECT: edit source
   nano /opt/jeannebrain/venzarai-router_config.yaml

   # BANNED: exec into container and edit
   # docker exec -it venzarai-router nano /app/config.yaml
   ```

3. **Make exactly one change at a time.**
   State the change in one sentence before making it. If you cannot describe it in one sentence, it is too many changes at once.

4. **Back up the file before editing.**
   ```bash
   cp /path/to/config /path/to/config.bak.$(date +%Y%m%d-%H%M%S)
   ```

5. **Rebuild the affected service only.**
   ```bash
   cd /path/to/docker-compose-dir
   docker compose up -d --build <service_name>
   ```
   Never run `docker compose up -d` without a service name — it may restart unrelated services.

6. **Wait for the service to reach running state (max 60 seconds).**
   ```bash
   sleep 10 && docker ps | grep <service_name>
   ```
   Must show `Up` — not `Restarting` or `Exited`. If not up in 60 seconds, read logs before continuing.

7. **Verify the endpoint responds.**
   Show the actual HTTP status code:
   ```bash
   # VenzariAI Router health
   curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:4001/health/liveliness

   # General service
   curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:<PORT>/<health_path>
   ```
   Expected: `HTTP 200`. Anything else is a failure — do not mark the task complete.

8. **Verify no regression on adjacent services.**
   Re-run `docker ps` and compare with before-state. All previously-`Up` containers must still be `Up`.

9. **Run a functional test if applicable.**
   For VenzariAI Router changes:
   ```bash
   curl -s -X POST http://localhost:4001/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"jeanne_primary","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
     -w "\nHTTP %{http_code} Time: %{time_total}s\n"
   ```

10. **Record the after-state (docker ps + curl output) as evidence.**
    This goes into `complete.sh`'s evidence argument.

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "I restarted the container, it should be fine." | "Should be" is not evidence. Show `curl` output with HTTP 200. |
| "The config looks right, so it will work." | Syntactically valid config ≠ functionally correct service. Show the endpoint response. |
| "I'll skip the backup — it's a minor change." | A minor change that breaks the service requires rollback. No backup = manual reconstruction. |
| "I rebuilt all containers to be safe." | Rebuilding all containers risks disrupting VenzariAI Router during long Ollama inference (GOLDEN RULE 17). Rebuild only the changed service. |
| "I don't need codegraph — I know this code." | codegraph finds callers and dependents you may not know exist. Run it even for familiar code. |
| "The endpoint didn't respond but the container is up, so it's probably fine." | Container up ≠ service healthy. A container can be `Up` while the process inside it is crashed. Show the curl output. |
| "It worked before my change, so the service is unrelated." | Show the before-state vs after-state comparison to confirm no regression. |

---

### Red Flags

Stop immediately and escalate to Billy if:

- The container does not reach `Up` status within 60 seconds of rebuild.
- The health endpoint returns anything other than HTTP 200 after rebuild.
- A previously-`Up` container is now `Exited` after the rebuild.
- The same change has been made three times and the service still does not respond (GOLDEN RULE 8).
- VenzariAI Router shows `unhealthy` in `docker ps` — this is a false positive during long Ollama inference. Do NOT restart it.

---

### Verification

Build-and-verify is complete when all of the following are documented:

```
# Before-state (actual docker ps output)
docker ps -a --format "table {{.Names}}\t{{.Status}}"

# After-state (actual docker ps output)
docker ps -a --format "table {{.Names}}\t{{.Status}}"

# Endpoint health (show actual curl output)
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:<PORT>/health
# Expected: HTTP 200

# No regression (confirm all previously-Up containers are still Up)
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

