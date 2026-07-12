# Layer 01 — Intelligence Runbook

**Last updated:** 2026-06-01 (task 0881 — OpenClaw model corrected to jeanne_primary)
**Layer stability:** LOCKED
**Domain:** OpenClaw, VenzariAI Router (:4001), Ollama, model routing, Telegram

---

## Model Identity Table (verified 2026-05-30)

| Model name | Size | Role |
|---|---|---|
| `jeanne-primary:latest` | 4.7 GB | PRIMARY — Qwen2.5 7B Q4_K_M, always warm. Used by jeanne-code CLI |
| `nomic-embed-text:latest` | 274 MB | Embeddings only |

**Policy:** One model always warm (OLLAMA_KEEP_ALIVE=-1). Never load two 4GB+ models simultaneously — combined RAM exceeds [your-vps-address]

---

## Model Routing Table (current as of 2026-05-30)

| Chain | Head model | Fallback chain | When used |
|---|---|---|---|
| `jeanne_primary` | `ollama_chat/jeanne-primary:latest` | → Groq → Mistral → OpenRouter → Claude | jeanne-code CLI, direct local inference |
| `jeanne_primary` | `ollama_chat/jeanne-primary:latest` | → Groq → Mistral → OpenRouter | **OpenClaw Telegram (primary)** — LOCAL FIRST per Rule 5 (fixed 2026-06-01) |
| `jeanne_fb_groq` | `groq/llama-3.3-70b-versatile` | → Mistral → OpenRouter → Claude → local Ollama | OpenClaw fallback only (was incorrectly set as primary) |
| `jeanne_fb_mistral` | `mistral/mistral-small-latest` | — | Groq fallback |
| `jeanne_fb_openrouter` | `openrouter/meta-llama/llama-3.3-70b-instruct:free` | — | Mistral fallback |
| `jeanne_fb_claude` | `anthropic/claude-haiku-4-5-20251001` | — | Last external resort |
| `claude-haiku-4-5-20251001` | `ollama_chat/jeanne-primary:latest` | — | jeanne-code model alias (local) |
| `claude-sonnet-4-6` | `ollama_chat/jeanne-primary:latest` | — | Settings.json default alias (local) |

**ADR-021 (REVISED 2026-06-01):** OpenClaw now uses `jeanne_primary` (local Ollama) as primary per Rule 5. The prior Groq-first config caused "empty response retries exhausted" when Groq had issues. EmbeddedAttemptSessionTakeoverError is prevented by keeping cron count at 9 (not by using Groq). OpenClaw restart confirmed healthy with jeanne_primary at 15:31 UTC 2026-06-01.

**Intent:** Local Ollama = PRIMARY for all inference (Rule 5). External APIs = fallback only.

---

## Fallback Chain Details (authoritative — sourced from VenzariAI Router config 2026-05-30)

### jeanne_primary (Telegram PRIMARY — fixed 2026-06-01)
```
1. ollama_chat/jeanne-primary:latest   (local Ollama — PRIMARY, Rule 5)
2. groq/llama-3.3-70b-versatile
3. mistral/mistral-small-latest
4. openrouter/meta-llama/llama-3.3-70b-instruct:free
```
- Ollama is HEAD. External = fallback only.
- Local model (~3s) avoids external API rate limits and empty response errors.

### jeanne_fb_groq (Fallback — NOT OpenClaw primary)
```
1. groq/llama-3.3-70b-versatile
2. mistral/mistral-small-latest
3. openrouter/meta-llama/llama-3.3-70b-instruct:free
4. ollama_chat/jeanne-primary:latest
```
- Use as explicit fallback only, not as OpenClaw default.

### jeanne_primary (Direct inference — Ollama-first)
```
1. ollama_chat/jeanne-primary:latest   (localhost:11434 on [your-vps-address]
2. groq/llama-3.3-70b-versatile
3. mistral/mistral-small-latest
4. openrouter/meta-llama/llama-3.3-70b-instruct:free
5. anthropic/claude-haiku-4-5-20251001
```

### DISABLED providers (do NOT re-enable without checking)
- **Gemini** — free-tier quota exhausted (returns 429 on all requests). NEVER add to fallback chains.
- **Moonshot** — account suspended (insufficient balance).
- **DeepSeek** — insufficient balance.

---

## OpenClaw Config Rules (HARDENED — read before touching openclaw.json)

**Config location (live):** `/home/billy/.openclaw/openclaw.json`
**Config location (repo):** `/opt/YOUR-PROJECT/configs/venzari-vps/openclaw.json`

Critical constraints that MUST NOT be violated:

| Rule | Detail |
|------|--------|
| NEVER add `liveTurnTimeoutMs` | This key caused a 2-day crash loop. Not a valid key in current OpenClaw version. Removing it fixed the crash. |
| NEVER add Gemini to fallback chains | Free-tier quota is permanently exhausted. Gemini in a chain causes silent 429 cascades that saturate other providers. |
| `timeoutSeconds: 90` in session config | Prevents Telegram from showing "bot not responding". Do not raise above 90 or lower below 60. |
| NEVER `kill -HUP 1` inside container | SIGHUP to PID 1 (tini) causes full gateway restart, killing all in-flight Telegram sessions. Use `openclaw config patch` only. |
| OpenClaw is WebSocket-only | Never call OpenClaw via REST. |

---

## VenzariAI Router Operations

### Health check
```bash
ssh venzari-vps-billy 'curl -sf http://127.0.0.1:4001/health/liveliness && echo "ROUTER OK"'
```

### Service status
```bash
ssh venzari-vps-billy 'sudo systemctl status venzarai-router'
```

### Restart (if needed — NOT during active inference)
```bash
ssh venzari-vps-billy 'sudo systemctl restart venzarai-router'
# Verify after restart:
ssh venzari-vps-billy 'curl -sf http://127.0.0.1:4001/health/liveliness && echo "ROUTER OK"'
```

### Inference test (via router)
```bash
ssh venzari-vps-billy 'curl -s http://127.0.0.1:4001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-venzarai-master-key" \
  -d '"'"'{"model":"jeanne_fb_groq","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'"'"' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[\"choices\"][0][\"message\"][\"content\"])"'
```

### Inference test via [your-vps-address]
```bash
curl -s http://127.0.0.1:4001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-venzarai-master-key" \
  -d '{"model":"jeanne_fb_groq","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
```

---

## Ollama Operations

### Check running models
```bash
ssh venzari-vps-billy "curl -s http://127.0.0.1:11434/api/tags | python3 -c \"import json,sys; [print(m['name'], m['size']) for m in json.load(sys.stdin)['models']]\""
```

### Warm up jeanne-primary model (keep alive forever)
```bash
ssh venzari-vps-billy "curl -s -X POST http://127.0.0.1:11434/api/generate \
  -d '{\"model\":\"jeanne-primary:latest\",\"prompt\":\"\",\"keep_alive\":\"-1\"}' | head -1"
```

### Quick inference test (direct Ollama, [your-vps-address]
```bash
ssh venzari-vps-billy "curl -s http://127.0.0.1:11434/api/generate \
  -d '{\"model\":\"jeanne-primary:latest\",\"prompt\":\"Say OK\",\"stream\":false}' \
  | python3 -c \"import json,sys; print(json.load(sys.stdin)['response'])\""
```

### Check Ollama RAM usage
```bash
ssh venzari-vps-billy "free -h && docker stats ollama --no-stream"
```

### Swap active model (requires LOCKED approval)
1. Write proposal to `.team/inbox/billy.jsonl`
2. After approval: update `jeanne-primary:latest` alias in Ollama
3. Update VenzariAI Router config if model name changes
4. Verify routing with inference test above

---

## OpenClaw Container Operations

### Status check
```bash
docker ps | grep openclaw
docker logs jeannebrain-openclaw-v5 --tail 30
```

### Restart (SAFE method — does not kill in-flight sessions)
```bash
# Preferred: compose restart (graceful)
cd /opt/YOUR-OPENCLAW/docker && docker compose restart
docker logs jeannebrain-openclaw-v5 --tail 20
```

**NEVER use `kill -HUP 1` inside the container** — SIGHUP to PID 1 (tini) propagates as a full gateway restart, killing all in-flight Telegram sessions.

### Check OpenClaw config
```bash
cat /home/billy/.openclaw/openclaw.json | python3 -m json.tool | head -40
```

Versioned config: `/opt/YOUR-PROJECT/configs/venzari-vps/openclaw.json`

**NEVER add `liveTurnTimeoutMs`** to openclaw.json — this key caused a 2-day crash loop. It is not a valid key in the current OpenClaw version.

### Check cron jobs (should be 9)
```bash
docker exec jeannebrain-openclaw-v5 cat /etc/cron.d/openclaw 2>/dev/null || \
  docker exec jeannebrain-openclaw-v5 crontab -l 2>/dev/null
```

---

## Telegram Debug Steps

When Telegram bot is not responding:

```bash
# Step 1: Is OpenClaw running?
docker ps | grep openclaw
docker logs jeannebrain-openclaw-v5 --tail 50 | grep -E "error|Error|warn|telegram"

# Step 2: Is SSH tunnel up? (port 4001 for VenzariAI Router)
ssh venzari-vps-billy 'curl -sf http://127.0.0.1:4001/health/liveliness && echo "ROUTER OK"'

# Step 3: Is Ollama running on [your-vps-address]
ssh venzari-vps-billy "curl -sf http://127.0.0.1:11434/api/tags | python3 -c \"import json,sys; print('OLLAMA OK, models:', len(json.load(sys.stdin)['models']))\""

# Step 4: Test full chain via VenzariAI Router
ssh venzari-vps-billy 'curl -s http://127.0.0.1:4001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-venzarai-master-key" \
  -d '"'"'{"model":"jeanne_fb_groq","messages":[{"role":"user","content":"test"}],"max_tokens":10}'"'"''

# Step 5: Check VenzariAI Router logs
ssh venzari-vps-billy 'sudo journalctl -u venzarai-router --since "10 minutes ago" | grep -i "quota\|429\|error"'
```

Common root causes (from 2026-05-27 outage):
- External API quota exhausted (Gemini, Groq) — check logs for 429 errors
- Duplicate cron jobs causing `EmbeddedAttemptSessionTakeoverError` — check cron count (should be 9)
- VenzariAI Router service down — check `systemctl status venzarai-router`

---

## Common Failures

### Failure: Ollama OOM / model not loading

```bash
ssh venzari-vps-billy "free -h"
# If < 2GB free:
ssh venzari-vps-billy "docker restart ollama"
# Only load jeanne-primary — never load two 4GB+ models simultaneously
```

### Failure: VenzariAI Router returns 502 or times out

```bash
# Check router health on [your-vps-address]
ssh venzari-vps-billy 'curl -sf http://127.0.0.1:4001/health/liveliness'
# Check service status:
ssh venzari-vps-billy 'sudo systemctl status venzarai-router'
# Check logs:
ssh venzari-vps-billy 'sudo journalctl -u venzarai-router --since "5 minutes ago" | tail -30'
# If genuinely crashed:
ssh venzari-vps-billy 'sudo systemctl restart venzarai-router'
```

### Failure: External API cascading failures

```bash
# Check which model is at head of jeanne_fb_groq:
ssh venzari-vps-billy 'sudo journalctl -u venzarai-router --since "5 minutes ago" | grep -i "routing\|head\|groq"'
# Groq should be HEAD for OpenClaw (jeanne_fb_groq chain)
# jeanne_primary chain should have Ollama as HEAD
```

---

## Telegram Commands

| Command | Action |
|---|---|
| /new | Start new conversation (clear context) |
| /remember [text] | Save fact to persistent memory |
| /recall [query] | Search memory, return matching facts |
| /forget [text] | Remove a memory entry |
| /stats | Show model, uptime, response stats |
| /swap [model] | Switch active model (triggers swap webhook) |

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
