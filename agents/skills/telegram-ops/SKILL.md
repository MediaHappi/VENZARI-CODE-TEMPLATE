---
name: telegram-ops
description: |
  Operational skill for Telegram bot management. Use for Telegram-specific operations beyond debugging — config changes, OpenClaw plugin management, and routine maintenance.
version: "2.0"
compatible-roles:
  - infrastructure
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read, Edit
---

# Skill: Telegram Operations

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Debug, verify, and maintain the [Your-AI-Name] Telegram bot. Covers OpenClaw plugin status,
send-telegram script, message flow, and end-to-end bot health.

---

### When to Use

- [Your-AI-Name] isn't responding to Telegram messages
- Morning/evening brief didn't arrive
- Testing whether OpenClaw is healthy
- Verifying send-telegram works after any config change
- After any openclaw.json change (MANDATORY verify)

---

### Key Facts

| Item | Value |
|---|---|
| Container | `jeannebrain-openclaw-v5` (Venzari VPS) |
| network_mode | `host` — MUST be host, never bridge (Rule 3) |
| Config | `/home/billy/.openclaw/openclaw.json` |
| Send script | `/usr/local/bin/send-telegram` |
| Bot token | `$BOT_TOKEN` (in /etc/profile.d/jeanne-env.sh) |
| Chat ID | `$TELEGRAM_CHAT_ID` (8442035442) |
| Log path | `docker logs jeannebrain-openclaw-v5 --tail 100` |
| FORBIDDEN | `liveTurnTimeoutMs` in openclaw.json — permanently banned (Rule 6) |

---

---

## Detail

### Process

### Check bot health

```bash
# 1. Container status
docker ps | grep openclaw
docker inspect jeannebrain-openclaw-v5 | python3 -c "import sys,json; d=json.load(sys.stdin)[0]; print('Status:', d['State']['Status'], '| Network:', list(d['NetworkSettings']['Networks'].keys()))"

# 2. Recent logs
docker logs jeannebrain-openclaw-v5 --tail 50

# 3. Plugin count (must be 9)
docker exec jeannebrain-openclaw-v5 ls /app/plugins/ 2>/dev/null | wc -l || echo "check logs"

# 4. Send test message
send-telegram "🔍 [Your-AI-Name] health check — $(date)"
```

### Send a Telegram message

```bash
send-telegram "<your message>"
# Or directly:
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}&text=<message>&parse_mode=Markdown"
```

### After openclaw.json change

```bash
# NEVER change openclaw.json without verifying Telegram after
# See: system-map/CURRENT_STATE.md — IMPORTANT note

docker restart jeannebrain-openclaw-v5
sleep 15
docker logs jeannebrain-openclaw-v5 --tail 20
send-telegram "✅ openclaw restarted — testing"
# Wait 30s for response
```

### Debug non-responsive bot

```bash
# Step 1: Check container
docker ps | grep openclaw || docker start jeannebrain-openclaw-v5

# Step 2: Check VenzariAI Router (openclaw routes through it)
curl -s http://127.0.0.1:4001/health/liveliness | grep alive

# Step 3: Check model in openclaw.json
python3 -c "import json; cfg=json.load(open('/home/billy/.openclaw/openclaw.json')); print('model:', cfg.get('model'))"
# Must be: venzarai-router/jeanne_primary

# Step 4: Check timeout
python3 -c "import json; cfg=json.load(open('/home/billy/.openclaw/openclaw.json')); print('timeout:', cfg.get('timeoutSeconds'))"
# Must be 300 or higher (liveTurnTimeoutMs MUST NOT exist)

# Step 5: Check for liveTurnTimeoutMs (banned key)
python3 -c "import json; cfg=json.load(open('/home/billy/.openclaw/openclaw.json')); print('BANNED KEY PRESENT' if 'liveTurnTimeoutMs' in cfg else 'OK — banned key absent')"
```

---

### Verification

```bash
# All must pass:
docker ps | grep openclaw | grep Up                      # container running
curl -s http://127.0.0.1:4001/health/liveliness          # VenzariAI Router up
send-telegram "✅ Telegram verified $(date '+%H:%M')"    # message sent (check Telegram)
```

---

## Reference

### Failure Runbook

| Symptom | Fix |
|---|---|
| Container not running | `docker start jeannebrain-openclaw-v5` then verify logs |
| Bot running but no response | Check VenzariAI Router health, check model=venzarai-router/jeanne_primary |
| Timeout errors in logs | Verify timeoutSeconds >= 300, remove liveTurnTimeoutMs if present |
| Network bridge mode | Rebuild with `network_mode: host` (Rule 3) |
| liveTurnTimeoutMs found | REMOVE IT IMMEDIATELY — Rule 6 |

---

