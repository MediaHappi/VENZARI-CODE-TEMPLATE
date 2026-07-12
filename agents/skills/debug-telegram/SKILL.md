---
name: debug-telegram
description: |
  Diagnose and fix Telegram/OpenClaw issues. Use when Telegram responses fail, OpenClaw container is unhealthy, or VenzariAI Router routing is broken. Covers openclaw.json config, container restart, and VenzariAI Router config fixes.
version: "2.0"
compatible-roles:
  - infrastructure
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read, Edit
---

# Skill: Telegram Debug

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Diagnose and resolve Telegram message failures in [YOUR-AI-NAME] by walking a fixed diagnostic ladder from OpenClaw logs through to Ollama, with known root causes from the 2026-05-27 incident documented.

---

### When to Use

- Telegram messages are not being received by [Your-AI-Name]
- [Your-AI-Name] receives messages but does not respond
- [Your-AI-Name] responds with errors or wrong content
- Response latency is > 30 seconds for a simple message
- Any Telegram-related alert in monitoring

---

---

## Detail

### Process

1. **Check OpenClaw container status first.**
   ```bash
   docker ps -a | grep openclaw
   docker logs jeannebrain-openclaw-v5 --tail 100
   ```
   Look for: `ECONNRESET`, `Connection refused`, `WebSocket error`, `timeout`.
   If the container is `Exited`: check the exit code with `docker inspect jeannebrain-openclaw-v5 | grep -A5 '"ExitCode"'`.

2. **Check the SSH tunnel (Venzari VPS → Venzari VPS).**
   The tunnel bridges Venzari VPS port → Venzari VPS VenzariAI Router :4001.
   ```bash
   # On Venzari VPS
   systemctl status venzarai-tunnel.service
   journalctl -u venzarai-tunnel.service -n 30
   ```
   Confirm `ServerAliveInterval` is ≤ 10 in the tunnel service config. If it is 60, that is the cause of ECONNRESET (GOLDEN RULE 28).

3. **Test VenzariAI Router directly (from Venzari VPS or via tunnel).**
   ```bash
   curl -s -X POST http://localhost:4001/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"jeanne_primary_warm","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
     -w "\nHTTP %{http_code} Time: %{time_total}s\n"
   ```
   Expected: HTTP 200. If timeout: check whether Ollama is warming up (normal up to 120s on first call).
   If HTTP 429 or provider error: check which fallback provider fired (see VenzariAI Router logs).

4. **Check VenzariAI Router logs for fallback chain behavior.**
   ```bash
   docker logs venzarai-router --tail 100 | grep -E "(fallback|error|model|provider)"
   ```
   Confirm `jeanne_primary_warm` HEAD is `ollama_chat/jeanne-primary:latest`.
   If Groq is firing as HEAD (not fallback), the warm chain config is wrong — this was the 2026-05-27 root cause #2.

5. **Check Ollama model availability.**
   ```bash
   # From Venzari VPS
   curl -s http://localhost:11434/api/tags | python3 -c "import json,sys; [print(m['name']) for m in json.load(sys.stdin)['models']]"
   ```
   Confirm `jeanne-primary:latest` is listed. If not: the model needs to be pulled.
   ```bash
   ollama pull jeanne-primary:latest && ollama create jeanne-primary -f /opt/ollama/Modelfile
   ```

6. **Check for duplicate cron entries.**
   ```bash
   crontab -l | grep -E "(jeanne|heal|telegram)"
   ```
   Each health/heal script must appear exactly once. Duplicate crons were the 2026-05-27 root cause #3 — they caused competing restarts and race conditions.

7. **Run jeanne-heal.sh (if steps 1-6 show no obvious single cause).**
   ```bash
   /usr/local/bin/jeanne-heal.sh --dry-run 2>&1
   ```
   Review the dry-run output. If it looks correct:
   ```bash
   /usr/local/bin/jeanne-heal.sh 2>&1
   ```
   Note: jeanne-heal.sh has a guard against restarting VenzariAI Router during active inference. Do not remove or bypass this guard.

8. **Send a test message via Telegram and measure latency.**
   After fixing, send a real test message to the [Your-AI-Name] bot and record:
   - Time sent
   - Time response received
   - Response content (confirm it is coherent, not an error message)
   This is the only valid end-to-end verification.

---

### Known Root Causes (2026-05-27 Incident)

These three causes produced a full Telegram outage. Know them. Check them first.

| # | Root Cause | How to Confirm | Fix |
|---|---|---|---|
| 1 | Gemini free-tier quota exhausted | VenzariAI Router logs show 429 from Gemini, cascading to silence | Remove Gemini from all fallback chains. Never re-add free-tier Gemini. |
| 2 | `jeanne_primary_warm` HEAD was Groq, not Ollama | VenzariAI Router logs show Groq firing as primary, not fallback | Edit venzarai-router_config.yaml: set `ollama_chat/jeanne-primary:latest` as HEAD with `request_timeout: 120` |
| 3 | Duplicate cron entries for jeanne-heal.sh | `crontab -l` shows the same script twice or more | Remove duplicates; keep exactly one entry per script |

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "Telegram is probably just slow." | Telegram API latency is < 1 second. If [Your-AI-Name] is silent for > 10 seconds, the cause is local, not Telegram. Check OpenClaw logs. |
| "The config looks right." | Config appearance is not service behavior. Run the VenzariAI Router inference test (Step 3). Show the response. |
| "VenzariAI Router is unhealthy in docker ps, so I'll restart it." | VenzariAI Router shows `unhealthy` during 90-150s Ollama inference. This is a false positive. Do NOT restart it. Check logs for actual errors first. |
| "I'll just restart OpenClaw." | Restarting OpenClaw kills all in-flight Telegram sessions. Only restart if logs show it is actually crashed (Exited), not just slow. |
| "It was working an hour ago, so the config must be fine." | Quota exhaustion (root cause #1) happens mid-session. Configs can be fine at 2 AM and broken at 2 PM. Check the current state, not the past state. |
| "jeanne-heal.sh will fix it." | jeanne-heal.sh handles container restarts. It does not fix misconfigured VenzariAI Router chains or duplicate crons. Follow the full diagnostic ladder. |

---

### Red Flags

Stop immediately and escalate to Billy if:

- OpenClaw has restarted > 3 times in the last hour without a clear cause.
- VenzariAI Router logs show all fallback providers failing (no successful inference in > 5 minutes).
- `jeanne-primary:latest` is missing from Ollama and the pull fails.
- You find duplicate cron entries that include `rm` or destructive operations.
- Any change you made has caused a previously-working service to stop responding.
- You have run through the full diagnostic ladder twice with no resolution.

---

### Verification

A Telegram fix is verified when ALL of the following are true:

```
# 1. OpenClaw container is running
docker ps | grep openclaw
# Expected: "Up X seconds" — not Restarting, not Exited

# 2. VenzariAI Router inference test passes
curl -s -X POST http://localhost:4001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"jeanne_primary_warm","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
  -w "\nHTTP %{http_code} Time: %{time_total}s\n"
# Expected: HTTP 200, response body contains a completion

# 3. End-to-end Telegram test
# Send a message to the [Your-AI-Name] Telegram bot
# Record: message sent at <time>, response received at <time>, latency <Xs>
# Response content: <actual response text>
```

Self-reported "it's working now" is not verification. Show all three outputs.

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

