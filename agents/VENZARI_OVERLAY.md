# Venzari Code Agent Skills — Overlay

This file is the central skill orchestration guide. It extends vendored skill systems
with project-specific context, role mappings, and selection heuristics.
Do NOT modify vendors/ directly — add overrides here.

**Full catalog:** [agents/SKILL_CATALOG.md](SKILL_CATALOG.md)
**Role policies:** [agents/roles/](roles/)

---

## Active Integration: skill_loader.py

**235 total skills loaded** by `ops/agent/skill_loader.py` (updated 2026-05-30):
- **20 [YOUR-AI-NAME]-native** skills in `agents/skills/` — v2.0 hybrid format
- **3 [YOUR-AI-NAME] operators** in `agents/operators/` — meta-skills for complex task patterns
- **23 agent-skills** vendor skills from addyosmani/agent-skills
- **24 mattpocock** skills across engineering, productivity, misc, personal, in-progress
- **38 ruflo** AI orchestration skills (ruvnet/ruflo) — agentdb, swarm, sparc, pair-programming
- **7 n8n-skills** (czlonkowski) — n8n workflow, expression, mcp, node config
- **29 zebbern** security/pentest skills — ethical hacking, cloud pentest, metasploit
- **73 trailofbits** security skills — smart contract auditing, supply chain, mutation testing
- **1 anthropics** — official Anthropic SKILL.md format specification (NEW)
- **15 alirezarezvani** — platform operations (container health, cron audit, ssh tunnel test, etc.) (NEW)
- **1 aman-bhandari** — rule obsolescence audit (NEW)
- **1 levnikolaevich** — hex-line hash-verified editing (NEW)

### Operators routing (NEW 2026-05-30)

Operators are meta-skills in `agents/operators/`. Use them instead of manually chaining skills:

| Task type | Use operator | Instead of manually chaining |
|---|---|---|
| Ship any infra/code change | `operators/deploy-feature` | worktree-task + build-and-verify + memory-write |
| Pre-release or post-incident review | `operators/audit-and-fix` | security-review + architecture-review + build-and-verify |
| Session start → task complete | `operators/claim-and-execute` | claim-task + inject_context + skill + verifier |

```bash
# List all 235 skills
python3 ops/agent/skill_loader.py list

# Count total
python3 ops/agent/skill_loader.py count

# Load a specific skill
python3 ops/agent/skill_loader.py load <skill-name>

# Search by keyword
python3 ops/agent/skill_loader.py find "security"
```

---

## Vendored Systems

| Vendor | Directory | Contents |
|---|---|---|
| agent-skills (addyosmani) | agents/vendors/agent-skills/ | 23 skills + 3 personas + hooks + 5 refs + docs |
| claude-code-harness | agents/vendors/claude-code-harness/ | s08 → ops/agent/context_compact.py |
| mattpocock-skills | agents/vendors/mattpocock-skills/ | 24 skills (recursive scan) |

### Agent-Skills Personas (NOT slash commands — role definitions)

| Persona | Path | Invoke for |
|---|---|---|
| `code-reviewer` | `agents/vendors/agent-skills/agents/code-reviewer.md` | Staff-level 5-dimension code review |
| `security-auditor` | `agents/vendors/agent-skills/agents/security-auditor.md` | OWASP-grounded security review |
| `test-engineer` | `agents/vendors/agent-skills/agents/test-engineer.md` | QA strategy and test coverage |

### Agent-Skills Reference Documents

| Reference | Path | Use when |
|---|---|---|
| orchestration-patterns | `vendors/agent-skills/references/orchestration-patterns.md` | Designing multi-agent flows |
| testing-patterns | `vendors/agent-skills/references/testing-patterns.md` | Writing test suites |
| security-checklist | `vendors/agent-skills/references/security-checklist.md` | Pre-deploy security gate |
| performance-checklist | `vendors/agent-skills/references/performance-checklist.md` | Performance verification |
| accessibility-checklist | `vendors/agent-skills/references/accessibility-checklist.md` | WCAG 2.1 AA audit |

**Orchestration rule (enforced):** Users orchestrate personas. Personas NEVER invoke other personas. Anti-patterns to avoid: Router Persona, Persona-Calling-Persona, Sequential Orchestrator. See `orchestration-patterns.md`.

---

## Role-to-Skill Mapping

Each agent role has a policy file in `agents/roles/` listing its primary and secondary skills.

| Role | Primary Skills | Role File |
|---|---|---|
| **discovery** | `reviewer`, `observability`, `architecture-review`, `mattpocock/engineering/triage` | [discovery.md](roles/discovery.md) |
| **infrastructure** | `infra`, `build-and-verify`, `worktree-task`, `observability`, `ai-model-ops` | [infrastructure.md](roles/infrastructure.md) |
| **backend** | `dashboard-ops`, `build-and-verify`, `worktree-task`, `business-automation` | [backend.md](roles/backend.md) |
| **frontend** | `dashboard-ops`, `build-and-verify`, `agent-skills/frontend-ui-engineering` | [frontend.md](roles/frontend.md) |
| **devops** | `worktree-task`, `build-and-verify`, `agent-skills/git-workflow-and-versioning`, `agent-skills/shipping-and-launch` | [devops.md](roles/devops.md) |
| **testing** | `reviewer`, `build-and-verify`, `telegram-ops`, `observability` | [testing.md](roles/testing.md) |
| **security** | `security-review`, `agent-skills/security-and-hardening`, `observability` | [security.md](roles/security.md) |
| **data** | `observability`, `reviewer`, `agent-skills/debugging-and-error-recovery` | [data.md](roles/data.md) |
| **memory** | `memory-write`, `reviewer`, `agent-skills/documentation-and-adrs` | [memory.md](roles/memory.md) |

---

## Skill Selection Quick Reference

| If you need to… | Skill |
|---|---|
| Start any task | `claim-task` (MANDATORY) |
| Infra change > 2 files | `worktree-task` |
| After any code/config change | `build-and-verify` |
| Telegram bot broken | `telegram-ops`, `debug-telegram` |
| VenzariAI Router/model change | `venzarai-router-config`, `ai-model-ops` |
| Dashboard broken | `dashboard-ops` |
| Security before push | `security-review` |
| End of task | `memory-write` |
| Gather unclear requirements | `agent-skills/interview-me` |
| Write spec before building (>30min) | `agent-skills/spec-driven-development` |
| Break down complex work | `agent-skills/planning-and-task-breakdown` |
| Implement without breaking anything | `agent-skills/incremental-implementation` |
| Adversarial review of arch decision | `agent-skills/doubt-driven-development` |
| Debug anything | `agent-skills/debugging-and-error-recovery` |
| Code review before PR | `agent-skills/code-review-and-quality` |
| Remove complexity | `agent-skills/code-simplification` |
| Security hardening | `agent-skills/security-and-hardening` |
| Retire/migrate old system | `agent-skills/deprecation-and-migration` |
| Ship to production | `agent-skills/shipping-and-launch` |
| TDD a component | `agent-skills/test-driven-development` |
| Diagnose codebase | `mattpocock/engineering/diagnose` |
| Architecture improvement | `mattpocock/engineering/improve-codebase-architecture` |
| Session handoff | `mattpocock/productivity/handoff` |

---

## Domain Quick Reference

**Infrastructure & Ops:** `infra`, `build-and-verify`, `worktree-task`, `deploy-script`, `observability`, `ai-model-ops`

**Telegram & OpenClaw:** `telegram-ops`, `debug-telegram`, `venzarai-router-config`

**Business & Content:** `business-automation`, `content-pipeline`, `dashboard-ops`

**Code Quality:** `agent-skills/code-review-and-quality`, `agent-skills/code-simplification`, `agent-skills/debugging-and-error-recovery`

**Security:** `security-review`, `agent-skills/security-and-hardening`

**Memory & Docs:** `memory-write`, `agent-skills/documentation-and-adrs`, `architecture-review`

**Engineering:** `mattpocock/engineering/tdd`, `mattpocock/engineering/diagnose`, `mattpocock/engineering/to-prd`, `mattpocock/engineering/to-issues`

**Productivity:** `mattpocock/productivity/handoff`, `mattpocock/productivity/write-a-skill`

---

## [YOUR-AI-NAME]-native Skills (18 total)

| Skill | When to use |
|---|---|
| `claim-task` | Start of every session (MANDATORY) |
| `memory-write` | After every task completion |
| `build-and-verify` | After any code change |
| `worktree-task` | >2 files or infra changes |
| `debug-telegram` | Telegram bot unresponsive |
| `venzarai-router-config` | Model routing changes |
| `infra` | Docker/SSH/cron changes |
| `observability` | RAM/disk/Grafana checks |
| `security-review` | Before any push |
| `architecture-review` | Warm chain integrity |
| `deploy-script` | Scripts to /usr/local/bin/ |
| `escalate` | 3 strikes on same fix |
| `reviewer` | Evidence verification |
| `ai-model-ops` | Ollama/VenzariAI Router model management |
| `telegram-ops` | Telegram bot operations |
| `dashboard-ops` | Flask/Celery/Redis maintenance |
| `business-automation` | n8n/HubSpot workflows |
| `content-pipeline` | AI content generation |

---

## Vendor Update Procedure

```bash
# Update agent-skills vendor from upstream:
cd /tmp && git clone --depth=1 https://github.com/addyosmani/agent-skills agent-skills-fresh
diff -rq --exclude='.git' agent-skills-fresh/ /opt/YOUR-PROJECT/agents/vendors/agent-skills/
# Review diffs, then copy changed files:
cp -r agent-skills-fresh/. /opt/YOUR-PROJECT/agents/vendors/agent-skills/
rm -rf /opt/YOUR-PROJECT/agents/vendors/agent-skills/.git
cd /opt/YOUR-PROJECT && python3 ops/agent/skill_loader.py count  # verify count
```

## Skill Discovery — Finding New Repos

```bash
# Run weekly scanner (searches GitHub for new skill repos):
bash /opt/YOUR-PROJECT/ops/agent/skill-scanner.sh

# Review the ranked candidate report:
cat /opt/YOUR-PROJECT/agents/vendors/SKILL_SCANNER_REPORT.md
```

The scanner searches GitHub for repos matching `agent-skills`, `claude-skills`, `ai-skills`, `llm-skills` patterns, ranks by stars + recency + SKILL.md presence, and outputs a candidate list for Billy to approve. It does NOT auto-clone. Weekly cron run recommended (Sunday 3am alongside memory-aging.sh).

See: `docs/governance/VENDOR_UPDATE_POLICY.md` for full procedure.

---

## BUILD Task Routing — GitHub-First Requirement (Rule 16)

**All BUILD tasks MUST invoke the `github-search` skill before starting implementation.**

```
BUILD task claimed
    ↓
1. Load github-search skill:
   python3 ops/agent/skill_loader.py load github-search
    ↓
2. Search GitHub for existing solutions (see SKILL.md protocol)
    ↓
3. Decision matrix:
   - Found exact solution     → copy code structure + security audit
   - Found partial solution   → adapt relevant parts
   - No relevant repos found  → build from scratch + document why
    ↓
4. If external code used: run security audit BEFORE commit:
   bash /opt/YOUR-PROJECT/ops/security/github-import-audit.sh <repo-dir>
    ↓
5. Add attribution comment if code was copied
```

**Why:** The [YOUR-AI-NAME] context-stripping proxy, model routing, and Ollama lifecycle management were all found on GitHub in 10 minutes (FreeSideNomad, nielspeter, mattlqx repos). Building from scratch would have taken hours.
