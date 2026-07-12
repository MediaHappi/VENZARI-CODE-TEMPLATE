# [YOUR-AI-NAME] Agent System V3 — 8-Specialist Model

**Version:** 3.0  
**Date:** 2026-06-21  
**Authority:** ADR-033 (Agent Harness Enhancement)  
**Status:** OPERATIONAL (Phase 5A complete)

---

## Overview

[YOUR-AI-NAME] operates as a **specialized multi-agent system** with 8 distinct agent personas, each optimized for a specific domain:

1. **Planner** — Complex work decomposition, architecture
2. **Code-Reviewer** — Code quality, style, efficiency
3. **Security-Reviewer** — Security audit, threat analysis
4. **Memory-Specialist** — L3 memory optimization, recall
5. **SRE-Specialist** — Infrastructure health, incident response
6. **Content-Specialist** — Documentation, markdown, wiki
7. **Intelligence-Specialist** — Code graph reasoning, impact analysis
8. **Infrastructure** — Generic tasks, fallback (catch-all)

All agents follow the **same task lifecycle** (claim → inject_context → execute → verify → complete) but apply domain expertise during execution.

---

## Agent Personas

### 1. Planner Agent

**Scope:** Complex work decomposition, architectural decisions, design review

**Invoked When:**
- Task is complex (>500 lines, multi-file, cross-layer)
- Untagged or ambiguous scope
- Architectural decision needed

**Specialization:**
- Breaks down complex tasks into sub-tasks
- Reviews architecture before implementation
- Identifies dependencies and blockers
- Routes work to specialists based on decomposed tasks

**Example:** Large refactoring task → Planner → breaks into sub-tasks → routes code changes to Code-Reviewer, infrastructure changes to SRE-Specialist

**Context Injection:** Full architectural context (ADRs, GOLDEN_RULES, MASTER-DIRECTIVE)

---

### 2. Code-Reviewer Agent

**Scope:** Code quality, style, efficiency, correctness

**Invoked When:**
- Code change submitted (any language)
- Post-implementation verification needed
- Style or performance issues detected

**Specialization:**
- Enforces code quality standards
- Identifies security anti-patterns (code-level)
- Detects performance issues
- Suggests efficiency improvements
- Runs /code-review skill automatically before completion

**Languages Supported:** Python, TypeScript, Shell, SQL, Markdown

**Context Injection:** Language-specific style guides, performance baselines, codebase patterns

---

### 3. Security-Reviewer Agent

**Scope:** Security audit, threat analysis, secret validation, hardening

**Invoked When:**
- Task is security-sensitive (auth, secrets, cryptography)
- Deployment to prod involves code changes
- Infrastructure changes affect attack surface
- /security-review skill needed before completion

**Specialization:**
- Threat modeling (STRIDE framework)
- Secret scanning and rotation verification
- Access control analysis
- Compliance checks (OWASP, NIST)
- Container and network hardening review

**Context Injection:** Security policies (GOLDEN_RULES Rule 13, MASTER-DIRECTIVE Section 5), threat models, compliance requirements

**Note:** Security-Reviewer is NOT invoked for simple operational tasks without code changes.

---

### 4. Memory-Specialist Agent

**Scope:** L3 memory optimization, semantic search, recall patterns, cache strategy

**Invoked When:**
- Task involves ChromaDB (L3 semantic memory)
- Memory performance degradation reported
- Session recall accuracy issues
- Memory governance violations detected

**Specialization:**
- Optimizes ChromaDB indexing and search
- Improves token efficiency (compression, aging)
- Designs retrieval strategies for task-scoped memory
- Manages memory layer integration across agents
- Implements contradiction detection and resolution

**Context Injection:** L3 memory architecture (5-layer model), ChromaDB schema, session logging format, memory governance rules

**Related ADR:** ADR-034 (Memory Layer Enhancements)

---

### 5. SRE-Specialist Agent

**Scope:** Infrastructure health, incident response, automation, reliability

**Invoked When:**
- Infrastructure task or incident
- Service health degradation
- Deployment or configuration change
- Self-healing automation needed
- Health check failure reported

**Specialization:**
- Diagnoses infrastructure issues (Docker, systemd, networking)
- Implements health checks and monitoring
- Automates incident recovery (self-healer.py integration)
- Manages service reliability and resilience
- Optimizes resource usage (CPU, memory, disk)

**Context Injection:** Infrastructure topology (VPS, Docker, systemd), service inventory, health check baselines, incident playbooks

**Related ADR:** ADR-036 (SRE & Self-Repair Automation)

---

### 6. Content-Specialist Agent

**Scope:** Documentation, markdown generation, wiki updates, knowledge transfer

**Invoked When:**
- Task requires documentation updates
- CURRENT_STATE.md needs updating
- Wiki ingestion needed
- Knowledge transfer documents required
- Runbook creation or update

**Specialization:**
- Writes clear, maintainable documentation
- Generates markdown from technical decisions
- Updates SSOT documents (CURRENT_STATE.md, runbooks, ADRs)
- Ingests findings into wiki
- Maintains documentation consistency

**Context Injection:** Documentation standards (markdown style, structure), CURRENT_STATE.md schema, wiki structure, runbook templates

**Related ADR:** ADR-037 (Content Workflows)

---

### 7. Intelligence-Specialist Agent

**Scope:** Code graph reasoning, impact analysis, symbol tracking, repository intelligence

**Invoked When:**
- Code intelligence queries (call graph, dependency analysis)
- Impact analysis needed (what breaks if I change this?)
- Repository-wide refactoring planned
- Symbol tracking or navigation needed

**Specialization:**
- Uses codegraph (RepoGraph patterns) for code understanding
- Traces call chains across modules
- Analyzes impact of changes
- Generates dependency matrices
- Supports IDE integration (Continue.dev patterns)

**Context Injection:** Codegraph database, codebase structure, module dependencies, impact analysis history

**Related ADR:** ADR-038 (Code Intelligence — Repository Reasoning)

---

### 8. Infrastructure Agent (Generic / Fallback)

**Scope:** All generic infrastructure tasks, fallback for unmatched work

**Invoked When:**
- No specialist matches the task
- Task type is ambiguous
- Legacy task without proper tagging
- Default behavior for catch-all

**Specialization:**
- Broad knowledge across all layers
- Executes work not matched to specialists
- Preserves backward compatibility
- Routes to specialists as needed during execution

**Context Injection:** Full system context (all layers, all specialists)

---

## Task Routing Logic

### How Task Type Is Detected

When a task is claimed, `inject_context.py` detects the task type via:

1. **Explicit tag** (if present): `security-sensitive`, `memory-layer`, `infrastructure`, etc.
2. **Keyword matching** in task title and description
3. **Layer detection** from task metadata
4. **Fallback** to Infrastructure agent if unmatched

### Routing Decision Tree

```
Task claimed
  ├─ Is it complex + untagged?
  │  └─ → Planner (decompose first)
  ├─ Does it involve code changes?
  │  ├─ Code-Reviewer (post-implement verification)
  │  └─ Infrastructure (execute changes)
  ├─ Is it security-sensitive?
  │  └─ → Security-Reviewer (threat analysis, hardening)
  ├─ Does it involve memory/L3?
  │  └─ → Memory-Specialist (optimization, governance)
  ├─ Is it infrastructure/incident?
  │  └─ → SRE-Specialist (health, automation)
  ├─ Does it require documentation?
  │  └─ → Content-Specialist (wiki, runbooks)
  ├─ Does it involve code intelligence?
  │  └─ → Intelligence-Specialist (graph, impact)
  └─ Else?
     └─ → Infrastructure (default)
```

### Post-Execution Routing

After a task agent executes, `inject_context.py` detects next-phase work:

- **Code changes + not reviewed?** → Code-Reviewer
- **Deploy needed?** → Infrastructure
- **Doc updates needed?** → Content-Specialist
- **Else?** → Close task

---

## Agent Execution Model

### Shared Lifecycle (All Agents)

1. **Claim:** Task pulled from `.tasks/` directory
2. **Context Injection:** `inject_context.py` merges system context + specialist knowledge
3. **Skill Loading:** Agent loads required skills from `agents/SKILL_CATALOG.md`
4. **Execution:** Agent performs work (code, deployment, documentation, etc.)
5. **Verification:** Running closing skill (`/code-review`, `/verify`, `/security-review`)
6. **Completion:** Task marked complete with evidence and documentation updates

### Specialist Knowledge Injection

Each specialist agent receives contextualized knowledge:

**Planner:**
- ADRs and architectural decisions
- MASTER-DIRECTIVE and GOLDEN_RULES
- Current system state and constraints

**Code-Reviewer:**
- Language-specific style guides
- Codebase patterns and conventions
- Performance baselines
- Code quality standards

**Security-Reviewer:**
- Threat models and risk assessment
- Compliance requirements (OWASP, NIST)
- Known vulnerabilities in dependencies
- Security policies

**Memory-Specialist:**
- L3 memory architecture and schema
- ChromaDB indexing strategies
- Session logging format
- Memory governance rules

**SRE-Specialist:**
- Infrastructure topology and service inventory
- Health check baselines
- Incident playbooks
- Reliability targets

**Content-Specialist:**
- Documentation standards
- SSOT document schemas
- Wiki structure and ingestion patterns
- Runbook templates

**Intelligence-Specialist:**
- Codegraph database and structure
- Module dependencies
- Call graph patterns
- Impact analysis history

---

## No Multi-Agent Swarm

**Important:** [YOUR-AI-NAME] does NOT spawn multiple agents per task (no "swarm").

- One task = one primary agent
- That agent may invoke specialists during execution (via skill system)
- Sequential execution only (per No-Swarm policy)

Example: Infrastructure agent executes deployment, then invokes Code-Reviewer skill for post-deploy verification. Not two parallel agents.

---

## Skill System Integration

Each agent has access to `agents/SKILL_CATALOG.md`, which indexes 24+ available skills organized by scope (code, memory, infrastructure, security, content, intelligence).

Agents select skills matching their domain:
- **Code-Reviewer** uses: code-review-and-quality, build-and-verify
- **Security-Reviewer** uses: security-review
- **Memory-Specialist** uses: memory-write, memory-query
- **SRE-Specialist** uses: infrastructure-health, self-repair
- **Content-Specialist** uses: documentation-update, wiki-ingest
- **Intelligence-Specialist** uses: code-graph-query, impact-analysis

---

## References

- **ADR-033:** Agent Harness Enhancement (Design)
- **MASTER-DIRECTIVE:** Section 9 (Task Drift Prevention)
- **GOLDEN_RULES.md:** Agent discipline rules
- **agents/SKILL_CATALOG.md:** Skill registry and metadata
- **ops/agent/inject_context.py:** Context injection and specialist routing
- **Task System:** `.tasks/` directory with agent assignment per task

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-03-15 | Initial 4-agent system (infrastructure, backend, frontend, devops) |
| 2.0 | 2026-06-03 | Added memory + security + intelligence agents (7 total) |
| 3.0 | 2026-06-21 | Finalized 8-specialist model (with generic fallback), routing logic documented |
