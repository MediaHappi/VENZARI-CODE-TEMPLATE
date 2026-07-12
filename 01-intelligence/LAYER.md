# Layer 01 — Intelligence

**Stability: LOCKED**  
**Domain:** OpenClaw, VenzariAI Router (:4001), Ollama, model routing, Telegram

---

## What This Layer Controls

- OpenClaw container (jeannebrain-openclaw-v5) — Telegram bot
- VenzariAI Router (:4001) — fallback chain orchestration
- Ollama inference engine (:11434) — local model serving
- openclaw.json — agent configuration
- venzarai router config — routing rules

## The Model Routing Vision

```
OpenClaw Telegram:  jeanne_fb_groq → Groq → Mistral → OpenRouter → Claude → Ollama (last resort)
Direct inference:   jeanne_primary → Ollama (LOCAL FIRST) → Groq → Mistral → OpenRouter → Claude
```

External APIs = cold start bridge ONLY. Local model = primary for direct inference.

## Current Models

| Model | Size | Role |
|---|---|---|
| jeanne-primary:latest | 4.7 GB | PRIMARY — Qwen2.5 7B Q4_K_M, always warm |
| nomic-embed-text | 274 MB | Embeddings only |

**Policy:** One model always warm (OLLAMA_KEEP_ALIVE=-1). No other large models loaded simultaneously.

## Critical Rules

1. openclaw.json: NEVER add `liveTurnTimeoutMs`
2. OpenClaw: MUST run in host network mode
3. VenzariAI Router: health check at :4001 (NOT :4001 — VenzariAI Router is gone)
4. Never restart venzarai-router during active inference

## Runbooks

- Telegram broken: `/opt/YOUR-PROJECT/01-intelligence/RUNBOOK.md`

---

## Live Inventory

| Service | VPS | Port | Config Path |
|---|---|---|---|
| VenzariAI Router | Memory | 4001 | /etc/venzarai/router.yaml ([your-vps-address]
| Ollama | Memory | 11434 | systemd: OLLAMA_KEEP_ALIVE=-1 |
| OpenClaw | Brain | WebSocket | /home/billy/.openclaw/openclaw.json |

Active model: `jeanne-primary:latest` (Qwen2.5 7B Q4_K_M, 4.7 GB)
Primary model group for Telegram: `jeanne_fb_groq` (Groq-first → Mistral → OpenRouter → Claude → Ollama)

---

## Layer Dependencies

← 00-foundation: SSH tunnel must be UP for VenzariAI Router access
← 02-memory: PostgreSQL stores conversation history
→ 03-workflow: n8n and content engine call VenzariAI Router via :4001
→ 04-ethical: model swap webhook updates Ollama model
