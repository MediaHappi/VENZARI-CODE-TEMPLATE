# Layer 04 — Ethical / Training Runbook

**Last updated:** 2026-05-30
**Layer stability:** LOCKED (Billy approval required for all changes)
**Domain:** Weekly training pipeline, production lock, governance, approval flows

---

## Production Lock

The following are frozen — NO changes without staging environment test + Billy explicit approval:

| Config | Location |
|---|---|
| Docker Compose files | All compose files on both VPS |
| `openclaw.json` | `/home/billy/.openclaw/openclaw.json` |
| `venzarai-router_config.yaml` | `/opt/venzarai-router/venzarai-router_config.yaml` |
| Model aliases | Ollama `jeanne-primary:latest`, `jeanne-primary:latest` |
| SSH tunnel systemd | `/etc/systemd/system/venzarai-tunnel.service` |
| `OLLAMA_KEEP_ALIVE` | Env var in Ollama container |
| `OLLAMA_MAX_LOADED_MODELS` | Env var in Ollama container |

### Approval Protocol

1. Write proposal to `.team/inbox/billy.jsonl`
2. Wait for explicit approval from Billy
3. Test in staging (worktree or separate branch)
4. Deploy with rollback plan ready
5. Verify with curl before declaring success

---

## Weekly Training Pipeline

Full pipeline documentation: `/opt/YOUR-PROJECT/docs/training/TRAINING_PIPELINE.md`

### Pipeline overview

```
Sunday 01:00 UTC  → jeanne-export-conversations.sh  (export new convos to HuggingFace)
Sunday 02:00 UTC  → jeanne-trigger-training.sh       (trigger fine-tune job on RunPod)
Mon-Thu  03:00-06:00 → jeanne-swap.sh               (swap in new model after training completes)
```

### 4-Step Training Ladder

Training follows a laddered curriculum — each step builds on the previous. See TRAINING_PIPELINE.md for full details.

| Step | Dataset | Size | Purpose |
|---|---|---|---|
| 1 | angrygiraffe/claude-opus-4.6-4.7-reasoning-8.7k | 8.7k | Distillation — teach `<think>…</think>` reasoning blocks |
| 2 | open-thoughts/OpenThoughts3-1.2M (sampled) | 100-200k | Scale and generalise reasoning |
| 3 | OpenDataArena/ODA-Mixture-100k | 101k | Polish and diversity |
| 4 | billy/jeanne-conversations | variable | Personalisation — real Telegram conversations |

Training: 1 epoch each (Step 4: 0.5 epoch). Lower learning rate on Step 3.
Base model: `jeanne-primary:latest`. Method: QLoRA (4-bit, r=16, alpha=32).

### Script locations

| Script | Live path | Repo path |
|---|---|---|
| `jeanne-export-conversations.sh` | `/usr/local/bin/jeanne-export-conversations.sh` | `/opt/YOUR-PROJECT/ops/venzari-vps/scripts/` |
| `jeanne-trigger-training.sh` | `/usr/local/bin/jeanne-trigger-training.sh` | `/opt/YOUR-PROJECT/ops/venzari-vps/scripts/` |
| `jeanne-swap.sh` | `/usr/local/bin/jeanne-swap.sh` | `/opt/YOUR-PROJECT/ops/venzari-vps/scripts/` |

### Check pipeline cron
```bash
crontab -l | grep -E 'export|training|swap'
```

### Run export manually (test)
```bash
/usr/local/bin/jeanne-export-conversations.sh 2>&1 | tail -20
```

### Monitor training trigger
```bash
cat /home/billy/.openclaw/logs/training.log 2>/dev/null | tail -30
```

---

## Model Swap Procedure

### Automated swap (via jeanne-swap.sh)
The swap script runs Mon-Thu 03:00-06:00 UTC. It:
1. Pulls the newly trained model from HuggingFace
2. Converts and registers it as an Ollama model
3. Updates the `jeanne-primary:latest` alias
4. Verifies inference works before declaring success
5. Rolls back if verification fails

### Manual swap (emergency)
```bash
# On [your-vps-address]
ssh venzari-vps-billy
# Pull new model (example: jeanne-primary:latest fine-tune)
ollama pull <new-model-name>
# Re-alias to jeanne-primary:latest (requires Modelfile)
echo "FROM <new-model-name>" > /tmp/Modelfile
ollama create jeanne-primary -f /tmp/Modelfile
# Verify:
curl -s -X POST http://127.0.0.1:11434/api/generate \
  -d '{"model":"jeanne-primary:latest","prompt":"Say OK","stream":false}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['response'])"
```

**Note:** `jeanne-primary:latest` is the canonical Ollama alias for the current production model (qwen2.5-coder:7b base). Always reference `jeanne-primary:latest` — never a specific model blob name. See `configs/ollama/MODEL-CONFIG.md` for current backing model details.

---

## Model Files Location ([your-vps-address]

```
/usr/share/ollama/.ollama/models/blobs/     ← model weight files
/usr/share/ollama/.ollama/models/manifests/ ← model manifest/alias files
```

Check disk space before pulling new models:
```bash
ssh venzari-vps-billy "df -h /usr/share/ollama/"
```

---

## Governance Rules

1. **Never load `jeanne-primary-coder:7b` and `jeanne-primary:latest` simultaneously** unless [your-vps-address]
2. **Never change `OLLAMA_KEEP_ALIVE` or `OLLAMA_MAX_LOADED_MODELS`** without staging test — these affect RAM directly.
3. **All model swaps require a rollback plan** — keep the previous model available by blob ID until new model is verified for 24 hours.
4. **jeanne-swap.sh includes a rollback guard** — do not remove it.

---

## Training Data Quality Thresholds

Quality gates applied during Step 4 data export (jeanne-export-conversations.sh):

| Filter | Threshold | Reason |
|---|---|---|
| Minimum exchange length | > 2 turns | Single-turn exchanges have low training signal |
| PII detection | Zero tolerance | No names, emails, phone numbers in training data |
| Duplicate filter | Deduplicated by hash | Prevents overfit on repeated messages |
| Minimum response length | > 20 characters | Filters "OK", "yes" responses |
| Validation gate (post-swap) | 3/3 test prompts pass | Must respond coherently before going live |

---

## Ethical Approval Workflow

Changes to training data sources, model architecture, or fine-tuning strategy require Billy's explicit written approval:

1. Propose change in `.team/inbox/billy.jsonl` with field `"type": "training-approval"`
2. Describe: what dataset, what change, why, expected impact
3. Billy approves/rejects in `.team/outbox/billy.jsonl`
4. Approved changes are tagged in git before applying
5. Rejected changes are logged but never applied

---

## Common Failures

### Failure: Training job triggered but model not available

**Problem:** `jeanne-trigger-training.sh` ran but no new GGUF appeared in Ollama.

**Diagnosis:**
```bash
# Check training logs:
ssh venzari-vps-billy "cat /home/billy/jeanne-backups/training*.log 2>/dev/null | tail -20"
# Check RunPod/Vast.ai job status (manual — check dashboard)
# Check if new model arrived in Ollama:
ssh venzari-vps-billy "curl -s http://127.0.0.1:11434/api/tags | python3 -c \"import json,sys; [print(m['name']) for m in json.load(sys.stdin)['models']]\""
# Check webhook receiver is running:
ssh venzari-vps-billy "docker ps | grep webhook || ps aux | grep webhook"
```

**Root Causes:**
- RunPod job ran out of credits
- HuggingFace token expired
- Webhook receiver not running on port 9000

**Resolution:** See "Runbook: Training Job Failed" below.

---

### Failure: Swap ran but jeanne-primary still returns old outputs

```bash
# Check which blob jeanne-primary:latest points to:
ssh venzari-vps-billy "curl -s http://127.0.0.1:11434/api/show -d '{\"name\":\"jeanne-primary:latest\"}' | python3 -c \"import json,sys; d=json.load(sys.stdin); print(d.get('modelinfo',{}).get('general.basename','unknown'))\""
# Compare to expected blob ID from vps-topology.md
```

---

### Failure: Export script fails (no HuggingFace token)

```bash
# Check env vars:
cat /home/billy/.openclaw/.env | grep -i hugging
# Must have HUGGINGFACE_TOKEN set
```

---

## Runbook: Training Job Failed

**Problem:** Fine-tune job did not complete or GGUF was not delivered.

**Diagnosis:**
```bash
# 1. Check trigger script logs
ssh venzari-vps-billy "cat /var/log/jeanne/training.log 2>/dev/null | tail -30"

# 2. Verify HuggingFace token
ssh venzari-vps-billy "huggingface-cli whoami 2>&1"

# 3. Check RunPod credits (manual — log into dashboard)
# https://www.runpod.io/console/overview

# 4. Check webhook receiver is alive
ssh venzari-vps-billy "curl -sf http://127.0.0.1:9000/health 2>/dev/null && echo 'WEBHOOK OK'"

# 5. Check training alerts in Grafana (Training Pipeline dashboard)
```

**Root Causes:**

| Symptom | Cause |
|---|---|
| HTTP 402 from RunPod | Insufficient credits |
| HTTP 401 from HuggingFace | Expired token |
| Webhook receiver not responding | Process crashed |
| GGUF downloaded but swap failed | Model file corrupt — check size |

**Resolution:**
```bash
# Retry with fallback GPU provider
ssh venzari-vps-billy "/usr/local/bin/jeanne-trigger-training.sh --provider vast 2>&1"

# If webhook receiver is down, restart it
ssh venzari-vps-billy "nohup python3 /usr/local/bin/jeanne-webhook-receiver.py &"

# If training alert threshold hit (2 consecutive failures) — Telegram alert will fire automatically
```

**Verify:**
```bash
# Confirm new model is registered in Ollama after retry
ssh venzari-vps-billy "curl -s http://127.0.0.1:11434/api/tags | python3 -c \"import json,sys; [print(m['name']) for m in json.load(sys.stdin)['models']]\""
```

**Rollback:**
```bash
# Keep using previous model — no rollback needed if swap never completed
# If swap completed but model is bad:
ssh venzari-vps-billy "/opt/jeanne-training/scripts/rollback-model.sh"
```

---

## Model Swap Workflow (Webhook-Triggered)

```
1. Weekly fine-tune job completes on RunPod
        ↓
2. Job POSTs to [your-vps-address]
        ↓
3. jeanne-webhook-receiver.py downloads GGUF
        ↓
4. ollama create jeanne-primary:latest -f Modelfile
        ↓
5. Smoke test: send 3 test prompts, verify coherent responses
        ↓
6. If PASS: keep new model, notify Telegram
   If FAIL: rollback to previous GGUF, alert Billy
```

---

## Swap Decision Criteria

| Metric | Threshold | Action |
|---|---|---|
| Test prompt pass rate | ≥ 3/3 | Proceed with swap |
| Test prompt pass rate | < 3/3 | Rollback, alert |
| Model file size | Within 10% of expected | Proceed |
| Model file size | >10% deviation | Alert — possible corrupt download |

---

## Training Schedule

| Job | Schedule | GPU | Duration |
|---|---|---|---|
| Weekly fine-tune | Sunday 3 AM | RunPod A100 | ~2-3 hours |
| Daily export | Daily 2 AM | None (CPU) | ~5 minutes |

---

## Rollback (Manual)

Previous GGUF kept for 7 days at `/opt/jeanne-training/models/previous/`.

```bash
# Manual rollback
ssh venzari-vps-billy "/opt/jeanne-training/scripts/rollback-model.sh"
```

---

## Ethical Guardrails

- No model shipped without smoke test passing (3/3 test prompts)
- Training data reviewed weekly for quality (human-in-the-loop)
- No training on sensitive PII conversations (filtered in export script)
- Fine-tuning only on locally owned conversation data
- Model versions tagged and retained for 30 days for audit

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

