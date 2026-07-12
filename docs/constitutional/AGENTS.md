# AGENTS.md — Universal Agent Operational Rules
## [Your Company] · [Your Product]

**Document Class:** Constitutional (Layer 3 — operational execution rules)  
**Update Frequency:** When governance rules change  
**Authority:** [Your Name] ([your-email])  
**Applies To:** ALL agents — OpenClaw, Claude Code, any future agent in the [YOUR-AI-NAME] ecosystem  
**Version:** 2.0 (2026-06-03)  
**Supersedes:** All prior AGENTS.md versions, workspace AGENTS.md v1

---

## PART I — SCOPE AND AUTHORITY

This document defines how ALL agents in the [YOUR-AI-NAME] ecosystem operate. It is the operational playbook, not a personality document (see SOUL.md for that) and not a structural blueprint (see ARCHITECTURE.md).

**Who this applies to:**
- OpenClaw — the Telegram/voice agent running on Venzari VPS inside the openclaw container
- Claude Code — the engineering agent running directly on Venzari VPS as the `billy` user
- jeanne-bridge — the inference proxy serving the V8 Dashboard
- Any future agents: voice, email, background tasks, swarm agents

**What this document governs:**
- Task lifecycle (how agents pick up, execute, and close work)
- Required workflows and validations
- Memory write policies (what goes where)
- Safety rules and escalation procedures
- Commit and repo interaction standards
- Tool usage rules
- Multi-agent coordination rules

---

## PART II — TASK LIFECYCLE

Every piece of work MUST have a task. No orphaned work. This is non-negotiable.

### 2.1 Standard Task Flow

```
1. CLAIM     → python3 ops/agent/task_manager.py claim "<agent_role>"
2. INJECT    → python3 ops/agent/inject_context.py "<task title>"
3. SKILL     → Load required_skills via skill_loader.py (MANDATORY before starting)
4. WORKTREE  → git worktree add .worktrees/{task_id} -b task/{task_id}
5. EXECUTE   → Do the work in the worktree, commit after every meaningful unit
6. VERIFY    → curl verify every changed endpoint; run tests if applicable
7. CLOSE     → Load closing skill (code-review, build-and-verify, or security-review)
8. DOC-SYNC  → Update relevant runbook, architecture doc, or CURRENT_STATE.md
9. COMMIT    → Commit SSOT first ([YOUR-AI-NAME]-CTO), then deploy to infrastructure
10. COMPLETE → python3 ops/agent/task_manager.py complete {id} "summary" --evidence "..."
11. CLEANUP  → git worktree remove .worktrees/{task_id} && git branch -d task/{task_id}
```

### 2.2 Required Fields for Task Creation

Every task in `.tasks/` MUST include:
- `id` — auto-assigned sequential integer
- `title` — ACTION: Layer — description (e.g., "BUILD: Dashboard chat SSE streaming")
- `layer` — which platform layer (00-constitutional, 01-infra, 02-inference, 03-inference, 04-dashboard, etc.)
- `agent_role` — one of: discovery, infrastructure, backend, frontend, devops, testing, security, data, memory
- `required_skills` — minimum 1 skill from `agents/SKILL_CATALOG.md`
- `description` — full context including references to relevant docs
- `dod` — definition of done as array of verifiable items

### 2.3 Task States

| State | Meaning |
|---|---|
| `pending` | Ready to be claimed |
| `in_progress` | Claimed and being worked on |
| `completed` | Done with evidence and docs updated |
| `blocked` | Cannot proceed — waiting on human or another task |

A task is NOT complete until:
1. Real evidence exists (curl HTTP 200, test output, log snippet)
2. Required skill was loaded and applied
3. Relevant documentation was updated
4. Closing skill was run

### 2.4 Skill Selection (MANDATORY)

Before starting any task:
1. Load required skills: `python3 ops/agent/skill_loader.py load <skill-name>`
2. Read the SKILL.md — this contains the exact procedure, verification commands, and failure runbook
3. Follow the skill workflow strictly

Skill-to-intent mapping:

| Intent | Primary Skill |
|---|---|
| New feature / build | `build-and-verify` → `spec-driven-development` |
| Infrastructure change | `worktree-task` → `infra` |
| Bug fix / debugging | `agent-skills/debugging-and-error-recovery` |
| Code review | `agent-skills/code-review-and-quality` |
| Documentation | `agent-skills/documentation-and-adrs` |
| Security change | `security-review` |
| Deployment | `build-and-verify` |
| Architecture decision | `agent-skills/doubt-driven-development` |
| New spec / feature spec | `agent-skills/spec-driven-development` |
| Multi-phase work (5+ tasks) | See `ops/agent/swarm-patterns.md` |

**Anti-rationalization rule:** These thoughts are incorrect and must be ignored:
- "This is too small to need a skill"
- "I can just quickly implement this"
- "I'll gather context first and then find a skill"

The correct behavior: always check for and load the applicable skill FIRST.

### 2.5 Closing Skills (MANDATORY before marking complete)

| Type of task | Closing skill |
|---|---|
| Any code change | `/code-review` (or `agent-skills/code-review-and-quality`) |
| Any deployment | `/verify` (confirm endpoints return HTTP 200) |
| Any security-relevant change | `/security-review` |
| All tasks | `task-completion-verifier` (mandatory final gate) |

---

## PART III — REQUIRED WORKFLOWS

### 3.1 Worktree Policy (Rule 9)

Non-trivial changes (>2 files, any infrastructure change) MUST use a git worktree:

```bash
git worktree add .worktrees/{task_id} -b task/{task_id}
# ... do work inside the worktree ...
git -C /opt/[YOUR-AI-NAME]-CTO/.worktrees/{task_id} add <files>
git -C /opt/[YOUR-AI-NAME]-CTO/.worktrees/{task_id} commit -m "task({id}): description"
# ... after task complete and merged ...
git worktree remove .worktrees/{task_id}
git branch -d task/{task_id}
```

Never do destructive work directly on main. Worktrees are the safety layer.

### 3.2 Commit Discipline (Rule 17)

- Commit after every logical unit of work — not at the end of a session
- Minimum: one commit per DoD item verified
- Never batch hours of changes into one end-of-session commit
- Push before ending any session
- Session-end checklist: `for w in /opt/[YOUR-AI-NAME]-CTO/.worktrees/*/; do git -C "$w" status --short 2>/dev/null | grep -q "." && echo "UNCOMMITTED: $w"; done`

### 3.3 SSOT-First Deployment (Rule 11)

Deployment order is non-negotiable:
1. Edit source in [YOUR-AI-NAME]-CTO worktree
2. Commit to [YOUR-AI-NAME]-CTO
3. Push to GitHub (origin main)
4. Apply to live infrastructure
5. Verify with curl

Never reverse this order. Never patch live infrastructure first.

### 3.4 GitHub-First Research (Rule 16)

Before building ANYTHING from scratch:
1. Run `agents/skills/github-search/SKILL.md`
2. Search for existing solutions
3. Copy structure, don't reinvent
4. If importing external code: run `ops/security/github-import-audit.sh`
5. Add attribution comment to any copied code

This rule exists because routing logic, proxy patterns, context-stripping, and model fallback logic are all solved problems on GitHub — building them from scratch wastes hours.

### 3.5 Documentation Update (Rule 16/18)

Before marking any task complete:
1. Run: `bash /usr/local/bin/jeanne-doc-drift-scan "<task-keyword>" --strict`
2. Update every doc the scanner flags as stale
3. If scanner returns exit 1, the task CANNOT be closed

Doc-type matrix (which doc to update):
| Change type | Primary doc to update |
|---|---|
| Infrastructure change | `system-map/CURRENT_STATE.md` + relevant runbook |
| API / route change | Relevant module doc + UNIFIED-ARCHITECTURE.md if structural |
| Model/routing change | `docs/architecture/UNIFIED-ARCHITECTURE.md` |
| New feature | Feature spec doc + CURRENT_STATE.md |
| Security change | `docs/security/` + CURRENT_STATE.md |
| Architecture decision | `docs/` ADR file |
| Constitutional change | `docs/constitutional/` (this directory) |

---

## PART IV — MEMORY WRITE POLICIES

Memory writes must be intentional and layered. Not everything belongs everywhere.

### 4.1 What Goes Where

| Memory Layer | Storage | Write When |
|---|---|---|
| L1 — In-context | Current conversation | Implicit — nothing to write |
| L2 — Session | PostgreSQL venzarai_hub.chat_messages | Every conversation turn (automatic via jeanne-api) |
| L3 — Semantic | ChromaDB / claude-mem :37877 | Validated engineering discoveries, debugging insights, business context |
| L4 — Structured | [YOUR-AI-NAME]-CTO docs / CURRENT_STATE.md | After every meaningful change; after every architecture decision |
| L5 — Institutional | [YOUR-AI-NAME]-CTO git history + ADRs | After every significant structural decision (tag with timestamp) |

### 4.2 CURRENT_STATE.md Update Protocol

Update CURRENT_STATE.md after:
- Any service goes up or down
- Any configuration changes
- Any deployment
- Any new task group created
- Any production incident

Format for updates:
```markdown
## Changes {date} Session
| Change | Status |
|---|---|
| {what changed} | ✅ DEPLOYED / ❌ FAILED / 🔧 IN PROGRESS |
```

### 4.3 What NOT to Write to Persistent Memory

Do NOT write to MEMORY.md, docs/, or L3/L4 stores:
- Transient debugging output
- Repetitive operational noise
- Assumptions not yet validated
- Duplicate information already present elsewhere
- Task-specific temp state (write to `.tasks/` instead)

### 4.4 Memory Validation Protocol

Before writing to L4/L5:
1. Confirm the information is validated (not assumed)
2. Check for duplicates — is this already documented somewhere?
3. Place it in the lowest (most specific) appropriate layer first
4. If it contradicts existing documentation, update the existing doc — don't create a parallel truth

---

## PART V — SAFETY, ESCALATION, AND ERROR HANDLING

### 5.1 Three-Strike Rule (Golden Rule 7)

If the same fix fails three times:
1. STOP immediately
2. Write to `.team/inbox/billy.jsonl`: `{"type": "escalation", "task": "{id}", "summary": "3 failures", "attempts": [...], "timestamp": "..."}`
3. Mark task as blocked: `python3 ops/agent/task_manager.py status {id}`
4. Do NOT attempt a fourth fix without human input

### 5.2 Destructive Action Protocol

Before any destructive action (delete, reset, drop, force-push, truncate):
1. Confirm the action is reversible or has a backup
2. Confirm this is explicitly in the task's DoD
3. Write what you are about to do and why
4. If in doubt: stop, write to inbox, escalate

Never do these without explicit instruction:
- `rm -rf` on any production path
- `docker system prune` or `docker volume rm`
- Database `DROP TABLE` or `TRUNCATE`
- `git reset --hard` on shared branches
- `git push --force` to main/master

### 5.3 Silent Failure Response (Rule 12)

If a container is restarting silently or a service is returning errors:
1. `docker logs {container} --tail 100` — read before touching anything
2. Identify the root cause before attempting any fix
3. Document the failure in CURRENT_STATE.md
4. Only then: apply fix, verify, document result

### 5.4 Rate Limit and External Service Failures

If Anthropic API returns 429 or rate limit errors:
- Switch to `jeanne-code` (routes to local Ollama via VenzariAI Router)
- Do NOT set `ANTHROPIC_BASE_URL` — this is permanently banned
- Do NOT proxy Claude Code through VenzariAI Router

If Groq/Mistral/external APIs fail:
- Route to local `jeanne-primary:latest` via VenzariAI Router
- Log the failure in CURRENT_STATE.md
- Do NOT silently drop the request

---

## PART VI — REPO INTERACTION STANDARDS

### 6.1 Commit Message Format

```
{type}(task-{id}): {short description}

{optional body: why this change was needed}
{optional: Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>}
```

Types: feat, fix, docs, infra, config, chore, wip  
WIP commits use `wip(task-{id}):` prefix and are rebased before final push when appropriate.

### 6.2 Branch Policy

- Main branch: `main` — always deployable
- Task branches: `task/{task_id}-{short-slug}` — created per task via worktree
- Never commit directly to main for non-trivial changes
- Squash or rebase task branches before merging when they have >3 WIP commits

### 6.3 External Code Import

All external code (from GitHub, npm, PyPI, etc.) MUST:
1. Pass `ops/security/github-import-audit.sh` security scan
2. Have an attribution comment: `# SOURCE: {repo_url} — {license}`
3. Be committed to [YOUR-AI-NAME]-CTO before deployment
4. Have no secrets, tokens, or hardcoded credentials

---

## PART VII — MULTI-AGENT COORDINATION

### 7.1 No Swarm Policy

Do NOT use multi-agent swarm for standard tasks. Swarm triples token usage.

Work sequentially unless explicitly approved by Billy.

Swarm is only appropriate for:
- Independent parallel tasks that have zero dependencies
- Phase work with 5+ truly parallel units
- Requires explicit `ops/agent/swarm-patterns.md` pattern

### 7.2 Agent Role Boundaries

| Agent | What it can do | What it cannot do |
|---|---|---|
| Claude Code | Full engineering — edit, deploy, test, commit | Send Telegram messages, modify OpenClaw workspace without task |
| OpenClaw | Chat with Billy, read workspace files, run bash, fix itself | Make git commits to [YOUR-AI-NAME]-CTO, modify V8 dashboard |
| jeanne-bridge | Proxy inference, inject SOUL.md system prompt | Modify workspace files, claim tasks |

### 7.3 Claude Code ↔ OpenClaw Coordination

Claude Code and OpenClaw share:
- `/opt/[YOUR-AI-NAME]-CTO` — the SSOT repo (both read it; Claude Code writes it)
- `/home/billy/.openclaw/workspace/SOUL.md` — Claude Code may update this as part of a task
- `/home/billy/.openclaw/workspace/MEMORY.md` — written by context-injector.py cron every 2 min

Claude Code does NOT:
- Write to `/home/billy/.openclaw/workspace/` without a task explicitly requiring it
- Restart OpenClaw container without first verifying it's actually broken
- Modify OpenClaw cron jobs without a task

---

## PART VIII — OPENCLAW-SPECIFIC OPERATIONS

*This section applies only to OpenClaw (the Telegram/voice agent inside the openclaw container).*

### 8.1 Container Environment

OpenClaw runs INSIDE the jeannebrain-openclaw-v5 container:
- Workspace mount: `/home/node/.openclaw/workspace/` = `/home/billy/.openclaw/workspace/` on host
- Docker socket is mounted — `docker ps` shows Venzari VPS containers only
- SSH is NOT installed inside the container — cannot `ssh root@158.220.105.107`
- To check Venzari VPS services: use `curl` directly to the endpoints

### 8.2 Model Routing (Current — VenzariAI Router)

OpenClaw routes ALL inference through VenzariAI Router at `http://localhost:4001/v1/chat/completions`:
- Primary: `jeanne-primary:latest` via Ollama on Venzari VPS
- Emergency fallback: Groq (configured in VenzariAI Router)
- Embeddings: `nomic-embed-text:latest` via Ollama

**Never route OpenClaw directly to Groq or any external API** — always use the VenzariAI Router so local-first policy is enforced.

### 8.3 Self-Modification

OpenClaw can edit its own workspace files when explicitly asked:
- Files at `/home/node/.openclaw/workspace/` (SOUL.md, AGENTS.md, MEMORY.md, TOOLS.md, etc.)
- Changes are picked up by OpenClaw on the next conversation turn
- DO NOT edit workspace files without being asked, unless it is part of an automated/scheduled task

### 8.4 Automation Rules

- NEVER send test messages to Telegram, email, or any external service during automated tasks
- NEVER modify files outside `/home/node/` without explicit permission
- NEVER run destructive commands: no `rm -rf`, no `docker system prune`, no `docker volume rm`
- ALWAYS end every response with a final text reply — even after tool calls

### 8.5 Known Scripts (Venzari VPS host)

Real scripts at `/home/node/scripts/` (= `/home/billy/scripts/` on host):
- `jeanne-healthcheck.sh` — Ollama stuck detection, auto-restart, 15-min cooldown
- `jeanne-session-cleanup.sh` — removes stale .lock files older than 2min
- `jeanne-self-upgrade.sh` — pulls latest OpenClaw image and restarts container
- `context-injector.py` — writes MEMORY.md every 2min with fresh memory search results
- `post_response_sync.py` — pushes chat entries to Venzari VPS vector store every 5min
- `jeanne-ram-monitor.sh` — checks Venzari VPS RAM, alerts via Telegram if < 2GB free

DO NOT reference or attempt to run: mrr_predictor.py, jeanne-dkg.py, jeanne-self-improve.py, whisper_memory.py — these do not exist.

---

## PART IX — WHAT THIS DOCUMENT IS NOT

AGENTS.md NEVER contains:
- Personality or identity content (→ SOUL.md)
- Architectural blueprints (→ ARCHITECTURE.md)
- Runtime state or deployment status (→ CURRENT_STATE.md)
- Infrastructure topology (→ SYSTEM_MAP.md)
- Curated engineering lessons (→ MEMORY.md)

---

*AGENTS.md v2.1 — [Your Company] · [Your Product] · 2026-06-03*  
*Synthesized from: workspace AGENTS.md v1, GOLDEN_RULES.md, CLAUDE.md, [YOUR-AI-NAME]-PLATFORM-MASTER-DIRECTIVE.md, TASK-DRIFT-PREVENTION.md, docs/governance/*
