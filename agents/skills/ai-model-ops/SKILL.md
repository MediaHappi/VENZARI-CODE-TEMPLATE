---
name: ai-model-ops
description: |
  Manage Ollama models and VenzariAI Router routing. Use when loading/unloading Ollama models, checking model health, or managing the jeanne-primary model lifecycle on Venzari VPS.
version: "2.0"
compatible-roles:
  - infrastructure
  - ai-trainer
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: AI Model Operations

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Manage Ollama models, VenzariAI Router routing config, and model swap procedures on the [YOUR-AI-NAME] platform.
Covers jeanne-primary chain management, coder model ops, and embedding model maintenance.

---

### When to Use

- Adding or removing a model from Ollama
- Changing model routing in `venzarai-router_config.yaml`
- Swapping the jeanne-primary:latest model (jeanne_primary_warm chain)
- Investigating model response quality or latency issues
- Configuring fallbacks or cooldown_time in VenzariAI Router
- Checking which model is answering requests

---

### Key Facts (read before any change)

| Item | Value |
|---|---|
| VenzariAI Router config | Venzari VPS: `/opt/venzarai-router/venzarai-router_config.yaml` |
| SSOT copy | Venzari VPS: `/opt/YOUR-PROJECT/configs/venzari-vps/venzarai-router_config.yaml` |
| Ollama endpoint | `http://127.0.0.1:11434` (Venzari VPS, tunneled to Brain :11434) |
| jeanne-primary:latest | `jeanne-primary:latest` (blob 357c53fb659c, 1.9 GB) |
| (removed) | jeanne-coder alias removed 2026-05-30 — use jeanne-primary:latest |
| FORBIDDEN | `jeanne-primary:latest` does NOT exist — use jeanne-primary-coder:7b directly |

---

---

## Detail

### Process

### Check current model state

```bash
# List loaded Ollama models (Venzari VPS)
"ollama list"

# Check VenzariAI Router model list
curl -s http://127.0.0.1:4001/v1/models -H "Authorization: Bearer sk-venzarai-master-key" | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"

# Check which model is answering jeanne_primary_warm
curl -s -X POST http://127.0.0.1:4001/v1/chat/completions \
  -H "Authorization: Bearer sk-venzarai-master-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"jeanne_primary_warm","messages":[{"role":"user","content":"say: model_check_ok"}],"max_tokens":5}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('model:', d.get('model'), '| response:', d['choices'][0]['message']['content'])"
```

### Change model routing (Rule 11: SSOT first)

```bash
# 1. Edit SSOT copy on Venzari VPS
nano /opt/YOUR-PROJECT/configs/venzari-vps/venzarai-router_config.yaml

# 2. Commit to YOUR-PROJECT
cd /opt/YOUR-PROJECT && git add configs/ && git commit -m "task/XXXX: update venzarai-router model routing"

# 3. Sync to Venzari VPS
scp /opt/YOUR-PROJECT/configs/venzari-vps/venzarai-router_config.yaml venzari-vps-billy:/opt/venzarai-router/venzarai-router_config.yaml

# 4. Restart VenzariAI Router
"docker restart venzarai-router"

# 5. Verify (wait 10s for startup)
sleep 10 && curl -s http://127.0.0.1:4001/health/liveliness && echo " ← VenzariAI Router UP"
```

### Pull a new Ollama model (Venzari VPS)

```bash
"ollama pull <model-name>"
# Verify: ollama list | grep <model-name>
```

### Check jeanne_primary_warm chain health

```bash
# jeanne_primary_warm should always start with Ollama (Rule 4)
grep -A20 "jeanne_primary_warm" /opt/YOUR-PROJECT/configs/venzari-vps/venzarai-router_config.yaml | grep "model:"
# First model in list must be ollama_chat/jeanne-primary — if not, it's a routing bug
```

---

### Verification

```bash
# All three checks must pass:
curl -s http://127.0.0.1:4001/health/liveliness | grep alive   # VenzariAI Router up
"ollama list"                             # Models loaded
curl -s -X POST http://127.0.0.1:4001/v1/chat/completions \
  -H "Authorization: Bearer sk-venzarai-master-key" \
  -H "Content-Type: application/json" \
  | python3 -c "import sys,json; print('FALLBACK OK' if json.load(sys.stdin).get('choices') else 'FAIL')"
```

---

## Reference

### Failure Runbook

| Symptom | Fix |
|---|---|
| VenzariAI Router returns 429 for jeanne_primary_warm | Check Ollama jeanne-primary:latest loaded: curl localhost:11434/api/ps |
| jeanne_primary_warm answering from Groq/external | Rule 4 violation — Ollama must be first in warm chain |
| Ollama model not found | `"ollama pull <model>"` |
| VenzariAI Router won't start after config change | `"docker logs venzarai-router --tail 50"` |
| `jeanne-primary:latest` error | Use `jeanne-primary-coder:7b` — jeanne-primary:latest does not exist |

---

