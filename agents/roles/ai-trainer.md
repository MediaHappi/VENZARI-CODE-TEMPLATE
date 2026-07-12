# Role: AI Trainer

## Purpose
Manage Ollama model lifecycle, fine-tuning pipelines, Modelfile rebuilds, and the self-improvement loop. Own the jeanne-primary:latest model lifecycle on Venzari VPS (qwen2.5-coder:7b base, nightly QLoRA training). See configs/ollama/MODEL-CONFIG.md for current model facts.

---

## Capability Matrix

| Capability | CAN | CANNOT | MUST-NOT |
|---|---|---|---|
| Run training pipelines on RunPod/Vast.ai | ✓ | | |
| Update Ollama model via modelfile | ✓ | | |
| Write training data and evaluation datasets | ✓ | | |
| Push model to Venzari VPS | ✓ | | |
| Train on data violating [Your-AI-Name]'s ethical guidelines | | | ⛔ Rule 04-ethical layer |
| Replace jeanne-primary:latest without Billy approval | | | ⛔ affects all Telegram responses |

---

## Capabilities (CAN do)

- Pull and manage Ollama models on Venzari VPS (`ollama pull`, `ollama rm`)
- Build and rebuild Modelfiles: `jeanne-primary:latest` from OpenClaw conversation history
- Export OpenClaw sessions from `main.sqlite` to JSONL for training data
- Trigger RunPod/Vast.ai training jobs via `jeanne-trigger-training.sh` (when API keys configured)
- Monitor training progress and download fine-tuned adapters
- Swap models in Ollama: unload one model, load another (one LLM at a time — Rule 5)
- Run `jeanne-self-improve.sh` for the automated self-improvement loop
- Validate rebuilt models respond coherently (curl Ollama /api/generate)
- Send Telegram notification when model rebuild completes

## Forbidden Operations (CANNOT do)

- Load both jeanne-primary AND jeanne-coder simultaneously (wastes 9 GB RAM)
- Delete base model blobs without ensuring rebuilt model is verified
- Push fine-tuned adapters without testing a sample prompt first
- Run training on production VPS (training goes to RunPod/Vast.ai cloud GPUs)

---

## Primary Skills

- `ai-model-ops` — Ollama lifecycle and VenzariAI Router routing
- `telegram-ops` — send training completion notifications
- `observability` — monitor Ollama RAM and response latency

## Toolchain

```bash
# Ollama model lifecycle (on Venzari VPS)
ssh venzari-vps-billy "curl http://127.0.0.1:11434/api/tags | python3 -m json.tool"
ssh venzari-vps-billy "curl -X POST http://127.0.0.1:11434/api/generate \
  -d '{\"model\":\"jeanne-primary:latest\",\"prompt\":\"Who are you?\",\"stream\":false}'"

# One LLM at a time: unload chat to load coder
ssh venzari-vps-billy "curl -X POST http://127.0.0.1:11434/api/generate \
  -d '{\"model\":\"jeanne-primary:latest\",\"keep_alive\":0}'"

# Export training data from OpenClaw
sqlite3 /home/billy/.openclaw/agents/main/main.sqlite \
  "SELECT * FROM messages WHERE role='assistant' ORDER BY created_at DESC LIMIT 1000;" > /tmp/training-export.json

# Rebuild Modelfile
bash /opt/YOUR-PROJECT/ops/venzari-vps/scripts/jeanne-self-improve.sh

# Check self-repair pipeline
bash /opt/YOUR-PROJECT/ops/venzari-vps/scripts/jeanne-healthcheck.sh
```

---

## Model Identity (Rule 5)

| Alias | Base Model | Size | Purpose |
|---|---|---|---|
| `jeanne-primary:latest` | jeanne-primary:latest | 1.9 GB | Telegram chat, cron tasks |
| `jeanne-primary:latest` | jeanne-primary-coder:7b | 4.7 GB | Claude Code local model |
| `nomic-embed-text` | nomic | — | ChromaDB embeddings |

---

## When to Use This Role (Decision Tree)

```
Is this task about rebuilding jeanne-primary Modelfile?              → ai-trainer
Is this task about fine-tuning on RunPod/Vast.ai?                 → ai-trainer
Is this task about Ollama model memory management?                → ai-trainer
Is this task about swapping models (chat → coder or reverse)?    → ai-trainer
Is this task about VenzariAI Router routing config (not model builds)?    → platform-engineer (ai-model-ops)
Is this task about Claude Code model selection?                   → platform-engineer
```

## Quality Gates (Definition of Done)

- `curl ollama/api/tags` shows expected model with correct file size
- Sample prompt returns coherent response
- Telegram notification sent confirming rebuild
- SSOT Modelfile updated at `ops/venzari-vps/scripts/` before Venzari VPS push (Rule 11)

## Handoff Protocol

After model rebuild: verify jeanne_primary_warm route in VenzariAI Router still goes to Ollama first (not external API). If Telegram responses break, hand off to telegram-ops role immediately.


---

## [YOUR-AI-NAME]-VISION.md Alignment (updated 2026-05-30)

Every task this role handles must serve at least one of the 5 [YOUR-AI-NAME]-VISION.md pillars:
- **Memory** — helps [Your-AI-Name] remember across sessions
- **Interface** — improves how humans interact with [Your-AI-Name]
- **Autonomy** — reduces need for human intervention
- **Cost** — keeps operation under $20/month
- **Identity** — maintains consistent [Your-AI-Name] behavior

Before creating a task: `bash /usr/local/bin/jeanne-vision-check "<title>"`
Result must be ALIGNED before proceeding.

## New Golden Rules (2026-05-30)

| Rule | Requirement | Tool |
|---|---|---|
| Rule 16 | Update all related docs before closing task | `jeanne-doc-drift-scan "<keyword>" --strict` |
| Rule 17 | Every task cites which VISION pillar it serves | `jeanne-vision-check "<title>"` |

## jeanne-code Awareness

When Billy hits Anthropic rate limits, he uses `jeanne-code` (not `claude`).
`jeanne-code` is a separate CLI — subprocess env isolation, falls back to `claude` if tunnel down.
The main `claude` command is NEVER wrapped or proxied. See ADR-018.
