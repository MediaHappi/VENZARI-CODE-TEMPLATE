# Agent Skill Catalog

**Total native skills: 21** | Updated: [FILL IN] | Source: `python3 ops/agent/skill_loader.py count`
**Vendor skill packs:** See `agents/vendors/` (216 skills across 10 collections — added in Phase 9c)
**Operators: 3** (deploy-feature, audit-and-fix, claim-and-execute) — see `agents/operators/`
**Skill format:** v2.0 Brief/Detail/Reference progressive disclosure

This is the authoritative skill reference. Agents consult this index when selecting skills for a task.
Load any skill: `python3 ops/agent/skill_loader.py load <skill-name>`

---

## Quick Reference — Pick by Task Type

| If you need to… | Use this skill |
|---|---|
| Start a task (MANDATORY) | `claim-task` |
| Any infra change (>2 files) | `worktree-task` → `build-and-verify` |
| Write memory after task | `memory-write` |
| Review logs / RAM / disk | `observability` |
| Security / secrets audit | `security-review` |
| Architecture coherence check | `architecture-review` |
| Deploy a feature safely | `operators/deploy-feature` |
| Pre-release audit + fix | `operators/audit-and-fix` |
| Full session: claim → complete | `operators/claim-and-execute` |
| Build + verify before PR | `build-and-verify` |
| Verify task is actually done | `task-completion-verifier` |
| Escalate to human | `escalate` |
| GitHub search / extraction | `github-search`, `github-reference-extraction` |
| Infrastructure operations | `infra` |
| Code / doc review | `reviewer` |
| Business automation | `business-automation` |
| Content pipeline | `content-pipeline` |
| Dashboard operations | `dashboard-ops` |
| Deploy scripts | `deploy-script` |
| AI model operations | `ai-model-ops` |
| LLM router config | `venzarai-router-config` |
| Telegram / bot integration | `telegram-ops`, `debug-telegram` |

---

## Section 1: Native Skills (21 skills, v2.0)

These are project-native, high-priority skills. Use these FIRST before reaching for vendor skills.

### Session Management

**`claim-task`** — Mandatory session start
- Claims next available task, injects all 6 memory layers, reads required skills + agent role
- Use at the START of every session
- Path: `agents/skills/claim-task/SKILL.md`

**`task-completion-verifier`** — Verify task is done
- Validates evidence, runs final checks before marking complete
- Path: `agents/skills/task-completion-verifier/SKILL.md`

**`escalate`** — Human escalation protocol
- Use when blocked >2 attempts, security decision required, or data destruction risk
- Path: `agents/skills/escalate/SKILL.md`

### Code Quality

**`build-and-verify`** — Build + test gate
- Run build system + full test suite before any commit or completion
- Path: `agents/skills/build-and-verify/SKILL.md`

**`worktree-task`** — Git worktree isolation
- Required for anything touching >2 files or infra — prevents cross-task contamination
- Path: `agents/skills/worktree-task/SKILL.md`

**`reviewer`** — Code + doc review
- Structured review checklist for PRs, docs, and architecture changes
- Path: `agents/skills/reviewer/SKILL.md`

### Memory & Knowledge

**`memory-write`** — Structured memory persistence
- Write findings to appropriate memory layer after completing any significant task
- Path: `agents/skills/memory-write/SKILL.md`

### Security

**`security-review`** — Security audit
- Secrets, injection, authentication, dependency audit
- Path: `agents/skills/security-review/SKILL.md`

**`architecture-review`** — Architecture decision review
- Coherence check before major structural changes
- Path: `agents/skills/architecture-review/SKILL.md`

### Infrastructure & Ops

**`infra`** — Infrastructure operations
- Path: `agents/skills/infra/SKILL.md`

**`observability`** — Logs, RAM, disk, health checks
- Path: `agents/skills/observability/SKILL.md`

**`deploy-script`** — Deployment scripting
- Path: `agents/skills/deploy-script/SKILL.md`

**`ai-model-ops`** — AI model operations
- Path: `agents/skills/ai-model-ops/SKILL.md`

**`venzarai-router-config`** — LLM router configuration
- Path: `agents/skills/venzarai-router-config/SKILL.md`

### Integrations

**`telegram-ops`** — Telegram bot integration
- Path: `agents/skills/telegram-ops/SKILL.md`

**`debug-telegram`** — Telegram debugging
- Path: `agents/skills/debug-telegram/SKILL.md`

**`github-search`** — Search GitHub repos via API
- Path: `agents/skills/github-search/SKILL.md`

**`github-reference-extraction`** — Extract and resolve GitHub refs
- Path: `agents/skills/github-reference-extraction/SKILL.md`

### Business

**`business-automation`** — Business process automation
- Path: `agents/skills/business-automation/SKILL.md`

**`content-pipeline`** — Content generation pipeline
- Path: `agents/skills/content-pipeline/SKILL.md`

**`dashboard-ops`** — Dashboard operations
- Path: `agents/skills/dashboard-ops/SKILL.md`

---

## Section 2: Operators (3 meta-skills)

Operators chain multiple skills. Use these instead of manually sequencing.

| Operator | Use instead of |
|---|---|
| `operators/deploy-feature` | worktree-task + build-and-verify + memory-write |
| `operators/audit-and-fix` | security-review + architecture-review + build-and-verify |
| `operators/claim-and-execute` | claim-task + inject_context + skill + verifier |

---

## Section 3: Vendor Skills

> **Phase 9c** installs 216 vendor skills into `agents/vendors/`.
> Until then, install manually: `cp -r /path/to/vendor-pack agents/vendors/<name>`

| Collection | Count | Domain |
|---|---|---|
| `agent-skills` (addyosmani) | 23 | General engineering patterns |
| `mattpocock` | 24 | TypeScript mastery, productivity |
| `ruflo` (ruvnet) | 38 | AI orchestration, SPARC framework |
| `n8n-skills` (czlonkowski) | 7 | n8n workflow automation |
| `zebbern-security` | 29 | Security / pentest patterns |
| `trailofbits` | 73 | Smart contract + supply chain security |
| `alirezarezvani` | varies | Platform operations |
| `aman-bhandari` | varies | Rule governance |
| `anthropics` | 1 | Official SKILL.md format spec |
| `levnikolaevich` | 1 | Hash-verified file editing |

---

*Powered by VENZARI CODE — venzari.dev*
