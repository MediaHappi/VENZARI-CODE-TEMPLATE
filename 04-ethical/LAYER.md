# Layer 04 — Ethical

**Stability: LOCKED (Billy approval required)**  
**Domain:** Governance, production lock, approval flows, safety

---

## Production Lock

The following are frozen — NO changes without staging + Billy approval:
- Docker Compose files
- openclaw.json
- venzarai-router_config.yaml  
- Model aliases
- SSH tunnel systemd
- OLLAMA_KEEP_ALIVE, OLLAMA_MAX_LOADED_MODELS

## Approval Protocol

For any LOCKED change:
1. Write proposal to `.team/inbox/billy.jsonl`
2. Wait for explicit approval
3. Test in staging (worktree or separate branch)
4. Deploy with rollback plan ready
5. Verify with curl before declaring success

## Runbooks

- Production hardening: `/opt/YOUR-PROJECT/04-ethical/RUNBOOK.md`

---

## Live Inventory

| Service | VPS | Port | Config Path |
|---|---|---|---|
| jeanne-training scripts | Memory | — | /opt/jeanne-training/ |
| jeanne-webhook-receiver.py | Memory | 9000 | systemd service |
| RunPod (GPU) | Cloud | — | ops/venzari-vps/scripts/jeanne-trigger-training.sh |
| Vast.ai (GPU fallback) | Cloud | — | ops/venzari-vps/scripts/jeanne-trigger-training.sh |

Training schedule: Sunday 3 AM ([your-vps-address]
Export schedule: Daily 2 AM ([your-vps-address]
HuggingFace: billy/jeanne-conversations, billy/jeanne-finetuned-models

---

## Layer Dependencies

← 00-foundation: [your-vps-address]
← 01-intelligence: Ollama receives new model after training
← 02-memory: PostgreSQL conversation data feeds training dataset
