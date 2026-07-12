# agents/ — Agent System Index

**Purpose:** [YOUR-AI-NAME]-native agent skills, coordination protocols, role definitions, and vendored agent frameworks.

**Skill total:** 230+ across 10 vendor sources + 24 native + 3 operators  
**Last updated:** 2026-05-30 | Source of truth: `SKILL_CATALOG.md`

---

## Directory Map

```
agents/
  skills/          [YOUR-AI-NAME] native skills (24) — use these first
  operators/       Meta-skills composing 2-4 skills (3) — for complex tasks  
  vendors/         External skill imports (10 sources)
    agent-skills/  addyosmani — spec-driven dev, TDD, debugging (23)
    mattpocock-skills/  TypeScript + productivity (24)
    ruflo-skills/  SPARC methodology, AgentDB, verification quality (38)
    n8n-skills/    n8n workflow patterns (7)
    zebbern-security/  Ethical hacking, pentest (29)
    trailofbits-skills/  Security auditing, skill-improver (73)
    anthropics/    Official Anthropic canonical format reference (1)
    alirezarezvani/ Multi-domain platform operations (15)
    aman-bhandari/ Rule obsolescence, concentric teaching (1)
    levnikolaevich/ Hash-verified editing (1)
  roles/           13 agent role definitions with capability matrices
  protocols/       Cross-role coordination protocols
  SKILL_CATALOG.md Auto-generated skill index — consult first
  SKILL_TEMPLATE.md Hybrid progressive-disclosure template for new skills
  PROJECT_OVERLAY.md Skill routing rules for orchestration
```

---

## Quick Start

```bash
# Count all skills
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py count

# List all skills
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py list

# Load a skill
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load claim-task

# Validate a skill's format
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py validate <skill-name>
```

---

## Legacy Directory Map (pre-2026-05-30)

| Directory | Status | Purpose |
|---|---|---|
| skills/ | Active (24 skills) | [YOUR-AI-NAME]-native skill workflows — task-specific procedures |
| operators/ | NEW (3 operators) | Meta-skills for complex task patterns |
| roles/ | Active (13 roles) | Agent role definitions with capability matrices |
| protocols/ | Active | Inter-agent communication protocols |
| vendors/ | Active (10 sources) | Vendored third-party agent frameworks |

---

## Key Files

| File | Purpose |
|---|---|
| PROJECT_OVERLAY.md | Bridge between [YOUR-AI-NAME] conventions and vendored systems |
| skills/INDEX.md | Master index of all available skills |
| protocols/AGENT_COMMUNICATION_PROTOCOL.md | Message format + task claiming protocol |
| vendors/README.md | Vendor classification (A/B/C) + integration points |

---

## How Agent Skills Work

1. Agent receives a task (from `.tasks/` queue via `ops/agent/claim.sh`)
2. Agent checks `agents/skills/` for a matching skill workflow
3. If found: follow the skill's step-by-step procedure
4. If not found: use general best judgment + create new skill when done
5. Complete task with evidence via `ops/agent/complete.sh`

---

## Adding a New Skill

1. Create `agents/skills/<skill-name>/` directory
2. Add `README.md` with: purpose, steps, evidence format, example
3. Add entry to `agents/skills/INDEX.md`
4. Reference from `PROJECT_OVERLAY.md` if it extends a vendored skill

---

## Vendored Systems

See `agents/vendors/README.md` for the full classification of the 3 vendored agent frameworks.

**Already integrated into YOUR-PROJECT:**
- `ops/agent/context_compact.py` — wraps `agents/vendors/claude-code-harness/s08_context_compact_improved.py`
- `ops/agent/task-poller-improved.py` — adapted from claude-code-harness coordination patterns

---

## Concurrency Rule (added 2026-07-02, task O0000000006)

**Do not run swarms or multiple concurrent implementation agents.** [YOUR-AI-NAME] uses one active
implementation agent per task, plus at most one advisor/helper call when review or planning
input is needed. This applies to every role, operator, and protocol in this directory — a real
gap found while making the agent framework executable: no existing file in `agents/` stated
this rule anywhere, despite it being repeated, explicit user direction across multiple
sessions. See `agents/protocols/task-lifecycle.md` for the full task lifecycle this rule
applies within.
