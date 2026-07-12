# [YOUR-AI-NAME] Agent Skills — Index
**Last updated:** 2026-05-29

Each skill is a named workflow with explicit exit criteria, red flags, and evidence requirements.
Load ONE skill at a time — do not load all at once.

**Do NOT use the bash snippets in this file directly.** They are superseded by the full SKILL.md files below.
Read the full SKILL.md for process steps, rationalizations, and verification requirements.

---

## MANDATORY SESSION STARTUP (run before any skill)

```bash
# 1. Pull latest repo
git -C /opt/YOUR-PROJECT pull

# 2. Read current state
cat /opt/YOUR-PROJECT/system-map/CURRENT_STATE.md

# 3. Inject 5-layer memory context (MANDATORY — do not skip)
python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "<task title or area you're working on>"

# 4. Check Rule 13 is active
# Claude Code is standalone — no ANTHROPIC_BASE_URL needed
```

`inject_context.py` queries L4 codegraph + L3 claude-mem + L5 decision-log. It is non-blocking — unavailable layers are skipped gracefully. **Never start work without running it.**

---

## Workflow Skills (full anatomy — read these)

| Skill | When to Use | File |
|---|---|---|
| **claim-task** | Start of every agent session — atomically claim next task + inject memory context | `agents/skills/claim-task/SKILL.md` |
| **build-and-verify** | Any change to source files → rebuild → verify HTTP (enforces GOLDEN RULE 2) | `agents/skills/build-and-verify/SKILL.md` |
| **memory-write** | After every task completion, root-cause discovery, or architectural decision | `agents/skills/memory-write/SKILL.md` |
| **escalate** | After 3 consecutive failures on the same task — three-strike protocol | `agents/skills/escalate/SKILL.md` |
| **worktree-task** | Non-trivial tasks (>20min) or any production config change — isolated git worktree | `agents/skills/worktree-task/SKILL.md` |
| **reviewer** | Read-only evidence verification after agent marks DoD complete | `agents/skills/reviewer/SKILL.md` |

---

## Infrastructure Domain Skills

| Skill | When to Use | File |
|---|---|---|
| **infra** | Docker containers, SSH tunnel, cron, nginx — check-before-touch discipline | `agents/skills/infra/SKILL.md` |
| **observability** | RAM, disk, Grafana, log monitoring — before/after any infra change | `agents/skills/observability/SKILL.md` |
| **security-review** | Secret scanning, SSH key audit, file permissions — before any push | `agents/skills/security-review/SKILL.md` |
| **architecture-review** | Warm chain integrity, orchestration coherence, no banned patterns | `agents/skills/architecture-review/SKILL.md` |
| **venzarai-router-config** | VenzariAI Router model group changes, fallback chain editing | `agents/skills/venzarai-router-config/SKILL.md` |
| **debug-telegram** | Telegram bot unresponsive, message delivery failures | `agents/skills/debug-telegram/SKILL.md` |
| **deploy-script** | Deploying scripts to /usr/local/bin/, cron setup | `agents/skills/deploy-script/SKILL.md` |

---

## Quick Reference (for one-liners only — see full skill for process)

### MANDATORY: 5-layer memory injection at task start
```bash
python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "<task title>"
# Expected: === INJECTED MEMORY CONTEXT === block with L4/L3/L5 sections
```

### L3 Memory write (after task completion)
```bash
python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py write \
  "Summary of what was done, what was learned, task-NNNN"
# NOT: memory_write.py (deprecated)
```

### L3 Memory read
```bash
python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py context "<query>"
# NOT: memory_query.py (deprecated)
```

### L4 Code intelligence
```bash
python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py context "<task description>"
python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py impact "<symbol_name>"
```

### Rule 13 — Claude Code clean-state check
```bash
pgrep -f "claude-venzarai-router-proxy" && echo "BAD: proxy running" || echo "OK: no proxy"
env | grep "^ANTHROPIC" && echo "BAD: env overrides present" || echo "OK"
# Claude Code is standalone — direct to api.anthropic.com, no VenzariAI Router
```

### Confirm Venzari VPS SSH alias
```bash
grep -A5 "venzari-vps-billy" ~/.ssh/config
# Expected: IdentityFile ~/.ssh/id_ed25519_brain_mesh
```

### Docker health check
```bash
ssh venzari-vps-billy "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

### VenzariAI Router endpoint test
```bash
curl -s -X POST http://localhost:4001/v1/chat/completions \
  -H "Authorization: Bearer sk-venzarai-master-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"jeanne_primary_warm","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
  -w "\nHTTP %{http_code} Time: %{time_total}s\n"
```

### Task operations
```bash
bash /opt/YOUR-PROJECT/ops/agent/list-tasks.sh pending
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py claim <AGENT_NAME>
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py complete <TASK_ID> "summary" --evidence "evidence"
```

### HITL blocking checkpoint (for security-sensitive actions)
```bash
bash /opt/YOUR-PROJECT/ops/agent/hitl_wait.sh <AGENT_NAME> <TASK_ID> "<action description>"
```

---

## Vendor Skills (23 additional skills from agent-skills + mattpocock)

**36 total skills available** (13 [YOUR-AI-NAME] + 23 vendor). Load any skill on demand:

```bash
# List all skills including vendor
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py list

# Load a specific vendor skill
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load agent-skills/debugging-and-error-recovery

# Search by keyword
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py find "security"
```

### Top 5 vendor skills for [YOUR-AI-NAME] tasks

| Situation | Vendor skill to use |
|---|---|
| Container/service broken | `agent-skills/debugging-and-error-recovery` |
| Before merging to main | `agent-skills/code-review-and-quality` |
| Security audit | `agent-skills/security-and-hardening` |
| Cleaning up code | `agent-skills/code-simplification` |
| Complex task planning | `agent-skills/planning-and-task-breakdown` |

See `agents/PROJECT_OVERLAY.md` for full vendor skill catalog and guidance.
