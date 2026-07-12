---
name: architecture-review
description: |
  Check for Golden Rules violations, SSOT drift, and role boundary violations. Use before major architecture decisions or post-incident review. Verifies system coherence against GOLDEN_RULES.md and CURRENT_STATE.md.
version: "2.0"
compatible-roles:
  - reviewer
  - infrastructure
  - platform-engineer
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Architecture Review — Coherence and Warm Chain Integrity

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Verify that [YOUR-AI-NAME]'s architecture is internally consistent: one orchestration system, Ollama-first warm chain, no competing memory stores, no banned patterns.

---

### When to Use

- After any change to VenzariAI Router config (`venzarai-router_config.yaml`)
- After any change to OpenClaw config (`openclaw.json`)
- After any new agent role or skill is added
- When `check-all.sh` shows unexpected failures
- Monthly coherence sweep

---

---

## Detail

### Process

1. **Read CONTEXT.md first.**
   Confirm all service names, ports, and VPS assignments before proceeding.

2. **Verify jeanne_primary_warm HEAD is Ollama-first.**
   ```bash
   "grep -A10 'jeanne_primary_warm' /opt/jeannebrain/venzarai-router_config.yaml | head -15"
   ```
   Expected: first model in the group is `ollama_chat/jeanne-primary:latest` with `timeout: 120`.
   Red flag: Gemini or any free-tier external model appearing anywhere in this group.

3. **Verify no competing orchestration systems.**
   [YOUR-AI-NAME] has exactly one orchestration layer: `.tasks/*.json` + `task_manager.py`. Check:
   ```bash
   # No second task queue
   find /opt/YOUR-PROJECT /home/billy -name "*.tasks" -o -name "tasks.db" 2>/dev/null | grep -v ".tasks"
   # No queen-agent pattern
   grep -r "queen\|swarm\|orchestrator_agent" /opt/YOUR-PROJECT/agents/ 2>/dev/null
   ```
   If a second orchestration system is found, escalate to Billy immediately.

4. **Verify no liveTurnTimeoutMs in openclaw.json.**
   ```bash
   grep -i "liveTurnTimeout" /home/billy/.openclaw/openclaw.json 2>/dev/null && echo "BANNED KEY FOUND — REMOVE" || echo "CLEAN"
   ```
   If found: remove it immediately. This key caused a 2-day crash loop.

5. **Verify no Gemini in any fallback chain.**
   ```bash
   "grep -i 'gemini\|google/gemini' /opt/jeannebrain/venzarai-router_config.yaml"
   ```
   Expected: no output. Gemini free-tier exhausts silently and cascades to full outage.

6. **Verify ChromaDB collections are not duplicated.**
   ```bash
   "curl -sf http://127.0.0.1:8001/api/v1/collections | python3 -m json.tool 2>/dev/null | grep name"
   ```
   Expected collections: `jeanne_obs_index`, `jeanne_obs_detail`, `jeanne_code_symbols`.
   If unfamiliar collection names appear, investigate before proceeding.

7. **Verify OpenClaw is not being called as REST.**
   ```bash
   grep -r "http://.*openclaw\|requests.get.*openclaw\|curl.*openclaw" /opt/YOUR-PROJECT/ops/ 2>/dev/null
   grep -r "http://.*openclaw\|requests.get.*openclaw\|curl.*openclaw" /home/billy/jeanne-venzari-vps/ 2>/dev/null
   ```
   OpenClaw is WebSocket-only. Any REST call to it will silently fail.

8. **Run check-all.sh and show full output.**
   ```bash
   bash /opt/YOUR-PROJECT/ops/monitoring/check-all.sh
   ```
   Expected: all checks PASS. Any FAIL is a blocking issue.

9. **Document coherence verdict.**
   Warm chain: OK/FAIL. Orchestration: single/COMPETING. Banned configs: clean/FOUND. check-all.sh: PASS/FAIL count.

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "The config looked right last time I checked." | Show the grep output now. Config files change. "Looked right" is not evidence. |
| "We only have one agent framework, so there's no duplication." | Don't assume — grep for duplicate agent/task-manager modules within YOUR-PROJECT itself (see task D0000000007) before declaring there's no duplication. |
| "Gemini is just in the fallback chain, so it's harmless." | Gemini free-tier exhausts quota silently. When it fails, it returns HTTP 429 without a clear signal, causing the whole chain to stall. Remove it. |
| "check-all.sh has been failing for days — it's a known issue." | A known failing check is an unacknowledged incident. Either fix it or explicitly document why it's expected to fail. Never normalize a red check. |
| "I only changed one service, so the rest of the architecture is fine." | Config interactions are non-obvious. Run check-all.sh. It takes 30 seconds. |

---

### Red Flags

Stop immediately and escalate to Billy if:

- `jeanne_primary_warm` HEAD is not `ollama_chat/jeanne-primary:latest` — warm chain integrity broken.
- `liveTurnTimeoutMs` found in `openclaw.json` — remove it before doing anything else.
- Gemini appears in any VenzariAI Router model group — remove before continuing.
- Two task queues or orchestration databases found — architecture is compromised.
- `check-all.sh` shows more than 2 FAIL items — systemic issue, not isolated.
- ChromaDB has > 6 collections — duplication or test pollution. Investigate before writing new data.

---

### Verification

Architecture review is complete when all of the following are documented:

```
# Warm chain head (show grep output)
grep -A5 'jeanne_primary_warm' venzarai-router_config.yaml | head -6
# Expected: first model = ollama_chat/jeanne-primary:latest

# No liveTurnTimeoutMs (show grep output or CLEAN)
grep -i "liveTurnTimeout" openclaw.json || echo "CLEAN"
# Expected: CLEAN

# No Gemini (show grep output or CLEAN)
grep -i "gemini" venzarai-router_config.yaml || echo "CLEAN"
# Expected: CLEAN

# check-all.sh (show full output)
bash /opt/YOUR-PROJECT/ops/monitoring/check-all.sh
# Expected: all PASS
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

