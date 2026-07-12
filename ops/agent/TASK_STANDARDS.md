# YOUR-AI Task Writing Standards

**Version:** 2.0 | **Rules:** 14, 15, 16 (GOLDEN_RULES.md) | **Updated:** 2026-05-30

Every task created in `.tasks/` must meet these standards before being claimed.

## Three New Mandatory Gates (added 2026-05-30)

### Gate A — Vision Alignment (BEFORE creating task)
```bash
bash /usr/local/bin/jeanne-vision-check "<task title>"
# Must return ALIGNED. DRIFTED = add vision pillar. FORBIDDEN = do not create task.
```

### Gate B — Doc Update in DoD (REQUIRED)
Every task that changes a system, process, or config MUST include in its DoD:
- At least one `UPDATE: [doc path] — [what section]` DoD item
- Which docs: see task-completion-verifier skill doc-type matrix

### Gate C — Approval Gate (for architecture/golden-rule/vendor tasks)
Before claiming a task that touches:
- GOLDEN_RULES.md, architecture docs, new vendor imports, Plan X implementations
```bash
bash /usr/local/bin/jeanne-approval-gate request "<title>" "<description>" <type>
# Creates APR-XXX entry. Do not proceed until status=approved.
```

---

---

## Required Fields

| Field | Type | Requirement |
|---|---|---|
| `id` | string | Auto-assigned by task_manager.py |
| `title` | string | See Title Format below |
| `layer` | string | One of: 00-foundation, 01-intelligence, 02-memory, 03-workflow, 04-ethical, 05-monitoring |
| `agent_role` | string | **REQUIRED** — one of the 9 roles (Rule 14) |
| `required_skills` | list | **REQUIRED** — minimum 1 skill from SKILL_CATALOG (Rule 14) |
| `description` | string | Minimum 100 characters, explains WHY not just WHAT |
| `dod` | list | Minimum 2 items, each verifiable with a command |

## Optional Fields

| Field | Type | When to use |
|---|---|---|
| `blocked_by` | list | Task IDs that must complete first |
| `group_id` | string | Fan-out/convergence grouping |
| `convergence_task` | string | Which task this unblocks |

---

## Title Format

```
PREFIX: ACTION — specific measurable outcome
```

Valid prefixes:
- `FIX:` — bug fix or broken thing
- `BUILD:` — new script, file, or capability
- `VERIFY:` — checking that something works (produces evidence)
- `UPDATE:` — modifying existing code or docs
- `HARDEN:` — making something more reliable
- `DOCUMENT:` — writing docs or runbooks
- `BACKFILL:` — retroactive update to existing things
- `SYNC:` — bringing two things into alignment

**Good:** `FIX: OpenClaw model not switching to warm — verify warmup_monitor.py HYSTERESIS_COUNT and Ollama /api/ps`  
**Bad:** `fix env var`

---

## Agent Role Selection

Choose from `agents/roles/` — see which role matches the work:

| Role | Work type |
|---|---|
| `discovery` | Read-only scanning, topology, inventory |
| `infrastructure` | Docker, systemd, SSH, nginx, cron |
| `backend` | Flask routes, Celery, API integrations |
| `frontend` | Jinja2 templates, CSS, JS |
| `devops` | git push, releases, rollbacks, CI/CD |
| `testing` | curl verification, health checks, regression |
| `security` | Secret scanning, permission audits |
| `data` | PostgreSQL, Redis, ChromaDB queries |
| `memory` | CURRENT_STATE.md, ADRs, L3 memory writes |

---

## Skill Selection

Open `agents/SKILL_CATALOG.md` → Quick Reference table → pick 1-3 skills.

Or use: `python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "<task title>" --layers l0`

**Rules:**
- `claim-task` is always implied (don't list it)
- `worktree-task` is required for >2 files or infra changes
- `build-and-verify` is required for any deployed change
- `memory-write` is implied at task end (don't list it)

---

## Definition of Done (DOD)

Each DOD item must be verifiable with a specific command or observable output.

**Good DOD items:**
```
"curl -s http://127.0.0.1:4001/health/liveliness | grep alive → HTTP 200"
"docker ps | grep openclaw | grep Up"
"test-claude-fallback.sh → 8 PASS / 0 FAIL"
"skill_loader.py count → 65"
```

**Bad DOD items:**
```
"it should work"
"deployed"
"verified"
```

Minimum 2 DOD items. Final item is always the git commit evidence.

---

## Evidence Format

Task completion evidence must include specific values, not assertions:

**Good:** `curl POST /v1/chat/completions model=jeanne_primary_warm → HTTP 200 response contains text`  
**Bad:** `tested and it works`

---

## Complete Example — Good Task

```json
{
  "title": "FIX: VenzariAI Router jeanne_primary_warm returns 500 — verify ollama jeanne-primary:latest loaded",
  "layer": "00-foundation",
  "agent_role": "infrastructure",
  "required_skills": ["ai-model-ops", "venzarai-router-config"],
  "description": "After Ollama container restart, jeanne-primary:latest is not loaded in RAM.
    VenzariAI Router jeanne_primary_warm route returns 500 because Ollama returns 'model not found'.
    Fix: warm up jeanne-primary:latest via a direct ollama pull or keepwarm ping, then verify
    the VenzariAI Router route returns HTTP 200.",
  "dod": [
    "ssh venzari-vps-billy curl localhost:11434/api/ps → jeanne-primary:latest present",
    "curl POST jeanne_primary_warm → HTTP 200, response received",
    "YOUR-PROJECT committed and pushed"
  ]
}
```

## Complete Example — Bad Task

```json
{
  "title": "fix the model thing",
  "layer": "00-foundation",
  "description": "model is broken fix it",
  "dod": ["fixed"]
}
```

Problems: no role, no skills, vague title, description < 100 chars, DOD not verifiable.

---

## CLI Usage

```bash
# Create with role and skills
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py create \
  "FIX: title here" \
  "00-foundation" \
  "description here (100+ chars explaining why)" \
  --role infrastructure \
  --skills "ai-model-ops,build-and-verify" \
  --dod "first verifiable check" "second verifiable check"

# Skill selection helper
python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "task title keywords" --layers l0
```

---

## How to Pick Layer

| Layer | Content |
|---|---|
| `00-foundation` | Infrastructure, environment, config, Claude Code reliability |
| `01-intelligence` | Skills, roles, agents, memory, AI model management |
| `02-memory` | Memory stack (L1-L5), context injection, knowledge |
| `03-workflow` | n8n, HubSpot, content engine, business automation |
| `04-ethical` | Training, alignment, quality thresholds |
| `05-monitoring` | Health checks, Grafana, observability, alerting |

---

## Task Completion Protocol (MANDATORY)

Before calling `python3 task_manager.py complete`, you MUST run the task-completion-verifier skill.

```bash
# Step 1: Load the verifier skill
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load task-completion-verifier

# Step 2: For each DoD item — verify with a real command, not an assertion
#   WRONG: "committed" / "tested" / "verified manually"
#   RIGHT: "curl http://127.0.0.1:4001/health → I'm alive!" 
#          "grep HYSTERESIS /opt/ai/warmup_monitor.py → HYSTERESIS_COUNT = 12"

# Step 3: Check canonical documents are updated
for doc in CURRENT_STATE.md CONTEXT.md changelog.md; do
  grep -q "$AFFECTED_TERM" /opt/YOUR-PROJECT/system-map/$doc && echo "✓ $doc" || echo "✗ needs update: $doc"
done

# Step 4: Verify artifact is DEPLOYED (SSOT commit ≠ deployed to VPS)
# For Venzari VPS changes: ssh venzari-vps-billy "verify command"
# For Venzari VPS changes: verify directly

# Step 5: ONLY THEN complete
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py complete TASK_ID \
  "What changed, where, and what's different from before." \
  --evidence "specific command → specific output; second command → second output"
```

**The full verifier checklist is in:** `agents/skills/task-completion-verifier/SKILL.md`

### Document Update Checklist (for every task that changes system behavior)

| Document | Check |
|---|---|
| `system-map/CURRENT_STATE.md` | Component status row updated |
| `CONTEXT.md` | Glossary/model groups/DO NOT table accurate |
| `system-map/changelog.md` | Entry added with task IDs |
| `0X-layer/RUNBOOK.md` | Procedures match new behavior |
| `GOLDEN_RULES.md` | Any rule that changed |
| `system-map/SERVICES_INVENTORY.md` | Service changes reflected |

## V2 Requirements (2026-06-02)

### GitHub-First Rule (MANDATORY)
Before implementing ANY feature:
1. Check repo-intelligence/patterns/ for existing patterns
2. Check repo-intelligence/reference-repos/ for reference implementations
3. Run: grep -r "KEYWORD" /opt/YOUR-PROJECT/repo-intelligence/ | head -10
4. Search GitHub manually if no pattern exists
5. Reference found patterns in task DoD

### Closing Skill Mandate (MANDATORY)
Every task MUST run a closing skill before marking complete:
- Code change: /code-review (Skill tool) or agents/skills/code-review-and-quality
- Deployment: /verify (Skill tool)
- Security-relevant: /security-review (Skill tool)
- Documentation: update CURRENT_STATE.md and write to L3 memory

### Enhanced Evidence Requirement
Evidence field in complete.sh must include at minimum:
- For deployments: `curl -w "%{http_code}" [url]` output showing 200
- For code: commit hash + brief test description
- For docs: file paths created/updated
