---
name: memory-write
description: |
  Write structured observations to L3 claude-mem semantic memory. Use after every task completion and after learning something non-obvious. Prevents knowledge loss between sessions. Writes to Venzari VPS :37877.
version: "2.0"
compatible-roles:
  - infrastructure
  - backend
  - devops
  - memory
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Memory Write — Capture Engineering Observations (L3)

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Write structured engineering observations to L3 after completing a task, discovering a root cause, or making an architectural decision. These observations survive sessions and inform future agents working on the same areas.

**Architecture:** Writes go to `claude-mem :37877` (HTTP service). claude-mem handles ChromaDB storage internally. Do NOT write directly to ChromaDB — always go through claude-mem.

**For permanent decisions (ADRs):** Also append to `docs/architecture/decision-log.md` (L5 Institutional).

---

### When to Use

- After every task completion (what was done, what failed, key files touched)
- After discovering a root cause for an incident
- After making an architectural decision (even a rejected approach is worth recording)
- After finding that a past assumption was wrong

---

---

## Detail

### Process

1. **Determine the observation type.**

   | Type | When |
   |---|---|
   | `observation` | General finding — something discovered about system state |
   | `fix` | A problem was solved — record what broke and what fixed it |
   | `decision` | An architectural or config decision was made |
   | `error` | A failure occurred — record what was tried and why it failed |
   | `milestone` | A phase or significant task was completed |

2. **Write a 50-word summary.**
   Be specific. Include: task ID, service name, what changed, outcome.
   Example: "Fixed VenzariAI Router config: moved jeanne_primary_warm HEAD to ollama_chat/jeanne-primary:latest. Was Groq-first (cold bridge). Telegram now uses local model. task-0019."

3. **Write the full detail.**
   Include: before-state, after-state, curl evidence, file paths touched, errors encountered, git commit hash.

4. **Write to L3 via claude_mem_adapter.py.**
   ```bash
   python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py write \
     "Fixed VenzariAI Router: jeanne_primary_warm HEAD moved to ollama_chat/jeanne-primary:latest from groq. Telegram uses local model. Evidence: HTTP 200 curl test. Commit abc1234. task-0019."
   ```
   Expected output: observation written to claude-mem (which stores in ChromaDB jeanne_memory collection)

5. **For architectural decisions — also write to L5.**
   ```bash
   # Append to decision-log.md
   cat >> /opt/YOUR-PROJECT/docs/architecture/decision-log.md << 'EOF'

   ### ADR-NNN: <Decision Title>
   **Date:** $(date -u +%Y-%m-%d)
   **Decision:** <one sentence>
   **Rejected:** <what was not chosen>
   **Why:** <reason>
   EOF
   git add docs/architecture/decision-log.md && git commit -m "docs: ADR-NNN ..."
   ```

6. **Confirm write succeeded.**
   ```bash
   python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py context "<key phrase from summary>"
   ```
   Expected: your observation appears in the returned context.

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "The fix is obvious, no one will forget it." | The next agent session has zero memory of this session. Write it now. |
| "claude-mem is unreachable." | Check ssh tunnel: `systemctl is-active venzarai-tunnel.service`. Fix tunnel first — do not skip L3 write. |
| "The summary is too long to be 50 words." | Edit it. 50 words is a constraint, not a suggestion. Compress. |
| "I'll write the memory after the next task." | Memory is most accurate immediately after the event. Write now. |
| "This was a failed approach — no point recording failures." | Failed approaches are the most valuable memory. Future agents won't repeat them. |

---

### Red Flags

Stop if:
- You are about to write a summary containing a live API key or password — sanitize first
- `claude_mem_adapter.py write` fails 3 times — check tunnel status, escalate if tunnel is down
- The observation detail is > 2000 tokens — summarize further

---

### Verification

Memory write is complete when:

```bash
# Write confirmation
python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py write "your summary here"
# Expected: "Memory written" or similar success output

# Read-back confirmation
python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py context "key phrase from summary"
# Expected: your observation appears in [L3 SEMANTIC] section
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

