---
name: venzarai-router-config
description: |
  Safe editing of VenzariAI Router configuration (jeanne-router.py). Use for model group changes,
  fallback chain editing, API key rotation, or health endpoint changes. Always backup before edit,
  restart service after, and verify with curl.
version: "2.0"
compatible-roles:
  - infrastructure
  - backend
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read, Write, Edit
---

# Skill: VenzariAI Router Config — Safe Edit Procedure

> **Version:** 2.0 | **Last verified:** 2026-06-22 | **Format:** Brief/Detail/Reference

---

## Brief

### Overview

VenzariAI Router is the inference gateway for all [YOUR-AI-NAME] services. It runs as a systemd service
(`venzarai-router.service`) and its source is SSOT-managed at `ops/router/jeanne-router.py`.

**Never edit the live file directly without backing up.** A bad config will take down all inference.

### When to Use

- Adding or changing model groups (e.g., `jeanne_primary`, `jeanne_fb_groq`)
- Editing fallback chains in model group definitions
- Rotating API keys or master key
- Changing health endpoint behavior
- Debugging why a model group is failing

---

## Detail

### Pre-Edit Checklist

```bash
# 1. Verify Router is currently healthy
curl -sf http://127.0.0.1:4001/health/liveliness && echo "OK" || echo "FAIL"

# 2. Check current model groups
curl -sf http://127.0.0.1:4001/v1/models -H "Authorization: Bearer sk-venzarai-router-master-key" | python3 -m json.tool

# 3. Read current source (SSOT — not live file)
cat /opt/YOUR-PROJECT/ops/router/jeanne-router.py | grep -n "model_groups\|jeanne_primary\|jeanne_fb_groq" | head -20

# 4. Backup live file
cp /opt/venzarai-router/jeanne-router.py /opt/venzarai-router/jeanne-router.py.bak.$(date +%Y%m%d_%H%M%S)
```

### Edit Flow (SSOT First — Rule 11)

```bash
# 1. Edit SSOT file in YOUR-PROJECT worktree
git worktree add .worktrees/router-config -b task/router-config
# Edit: .worktrees/router-config/ops/router/jeanne-router.py

# 2. Commit SSOT change first
cd .worktrees/router-config
git add ops/router/jeanne-router.py
git commit -m "config(router): <what changed and why>"

# 3. Merge to main branch
cd /opt/YOUR-PROJECT && git merge task/router-config --no-ff

# 4. Deploy to live (copy from SSOT to runtime location)
cp /opt/YOUR-PROJECT/ops/router/jeanne-router.py /opt/venzarai-router/jeanne-router.py

# 5. Restart service
sudo systemctl restart venzarai-router.service

# 6. Verify health (MANDATORY — never skip)
sleep 3
curl -sf http://127.0.0.1:4001/health/liveliness && echo "HEALTHY" || echo "FAIL — check logs"
sudo journalctl -u venzarai-router.service --since "2 minutes ago" --no-pager | tail -20

# 7. Test inference with a real model call
curl -s http://127.0.0.1:4001/v1/chat/completions \
  -H "Authorization: Bearer sk-venzarai-router-master-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"jeanne_primary","messages":[{"role":"user","content":"ping"}],"max_tokens":10}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('OK:', r['choices'][0]['message']['content'])"
```

### Rollback If Health Check Fails

```bash
# Restore backup
cp /opt/venzarai-router/jeanne-router.py.bak.<TIMESTAMP> /opt/venzarai-router/jeanne-router.py
sudo systemctl restart venzarai-router.service
sleep 3
curl -sf http://127.0.0.1:4001/health/liveliness && echo "RESTORED" || echo "STILL BROKEN — escalate to Billy"
```

---

## Reference

### Key Files

| File | Purpose |
|---|---|
| `/opt/YOUR-PROJECT/ops/router/jeanne-router.py` | SSOT source — edit this first |
| `/opt/venzarai-router/jeanne-router.py` | Live runtime file — deploy after SSOT commit |
| `/opt/venzarai-router/.env` | API keys (GROQ_API_KEY, ANTHROPIC_API_KEY, etc.) |
| `systemctl status venzarai-router.service` | Service health |

### Health Endpoints

| Endpoint | Expected | Meaning |
|---|---|---|
| `GET /health/liveliness` | HTTP 200, empty body | Router process alive |
| `GET /v1/models` | JSON list of model groups | Available models |
| `POST /v1/chat/completions` | `{"choices":[...]}` | Inference working |

### Active Model Groups (as of 2026-06-22)

- `jeanne_primary` — local Ollama via `jeanne-primary:latest` (golden rule: LOCAL FIRST)
- `jeanne_fb_groq` — Groq external (fast, external cost)
- `embed` — embedding via `nomic-embed-text` through Ollama

### Golden Rules That Apply

- Rule 4: VenzariAI Router is the inference gateway — all inference through :4001
- Rule 5: Two model policy — ONLY `jeanne-primary:latest` + `nomic-embed-text` in Ollama
- Rule 11: SSOT first — commit to `ops/router/jeanne-router.py` BEFORE copying to live
- Rule 2: Verify with curl after every change — `HTTP 200` is verification

### Red Flags — Stop and Escalate

- Router restarts more than 3 times after a config change → activate Rule 7 (three-strike)
- `journalctl` shows `ImportError` or `SyntaxError` → syntax error in edited file, rollback immediately
- `/health/liveliness` returns anything other than 200 → rollback, do not proceed
- Any existing Telegram messages fail after config change → inference broken, rollback
