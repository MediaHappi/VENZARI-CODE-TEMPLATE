---
inclusion: always
---

# Structure Steering

## Repository layout

```
YOUR-PROJECT/
├── agents/
│   ├── skills/          ← 21+ native skills (claim-task, build-and-verify, etc.)
│   ├── vendors/         ← 216 vendor skills (agent-skills, mattpocock, ruflo, etc.)
│   ├── roles/           ← 15 agent role files
│   ├── operators/       ← 3 operator chains (deploy-feature, audit-and-fix, claim-and-execute)
│   ├── protocols/       ← 6 protocol docs (task-lifecycle, memory-governance, etc.)
│   ├── SKILL_CATALOG.md ← authoritative skill index
│   └── VENZARI_OVERLAY.md ← skill selection heuristics
├── ops/agent/           ← task lifecycle scripts, skill loader, gates, memory
├── interfaces/
│   ├── slack/           ← Slack bot + webhook integration
│   └── shared/          ← shared event publisher, session manager
├── docs/
│   ├── constitutional/  ← SOUL.md, ARCHITECTURE.md, AGENTS.md, DOCUMENT-GOVERNANCE.md
│   ├── wiki/            ← incidents/, entities/, sources/
│   ├── runbooks/        ← TEMPLATE.md, ROLLBACK.md, SESSION_BOOT_SEQUENCE.md
│   ├── adr/             ← Architecture Decision Records
│   ├── evidence/        ← task evidence files
│   └── handoffs/        ← session handoff notes
├── 00-foundation/       ← RUNBOOK.md, LAYER.md — VPS, SSH, infra layer
├── 01-intelligence/     ← RUNBOOK.md, LAYER.md — code graph, AI reasoning
├── 02-memory/           ← RUNBOOK.md, LAYER.md, memory_schema.md
├── 03-workflow/         ← RUNBOOK.md, LAYER.md — tasks, skills, agents
├── 04-ethical/          ← RUNBOOK.md, LAYER.md — governance, SOUL
├── 05-monitoring/       ← RUNBOOK.md, LAYER.md — alerts, health checks
├── system-map/
│   ├── CURRENT_STATE.md ← ⭐ READ THIS FIRST every session
│   ├── SERVICES_INVENTORY.md
│   └── changelog.md
├── .tasks/              ← task JSON files (task_manager.py writes here)
├── .venzari/
│   ├── agents/          ← agent reflections
│   ├── hooks/           ← git hooks
│   └── skills/          ← project-local skill overrides
├── .kiro/
│   ├── steering/        ← product.md, tech.md, structure.md (this file)
│   └── hooks/           ← quality-gates.json
├── .codegraph/          ← code graph snapshots
├── .advisors/           ← advisor session outputs
├── .team/
│   ├── inbox/           ← agent-to-human escalation queue
│   └── knowledge/       ← accumulated project knowledge
└── .approvals/          ← tiered approval requests
```

## Naming conventions

- Task IDs: `TASK-XXXX` (4-digit, zero-padded)
- Branch names: `task/TASK-XXXX`
- Worktrees: `.worktrees/TASK-XXXX`
- Skill names: `kebab-case`
- Agent roles: `kebab-case` (backend, devops, security, etc.)

## File creation rules

- Always check `system-map/CURRENT_STATE.md` before starting
- Task JSON lives in `.tasks/` — never duplicate into other dirs
- Evidence files go in `docs/evidence/TASK-XXXX-evidence.md`
- Handoffs go in `docs/handoffs/HANDOFF-YYYY-MM-DD.md`
- ADRs: `docs/adr/ADR-XXX-short-title.md`
- Runbooks: `docs/runbooks/TOPIC.md`
