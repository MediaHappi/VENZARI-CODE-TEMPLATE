# DOCUMENT-GOVERNANCE.md — Constitutional Document Governance
## [Your Company] · [Your Product]

**Document Class:** Constitutional (meta — governs the constitutional document system)  
**Update Frequency:** Rarely — when document hierarchy changes  
**Authority:** [Your Name] ([your-email])  
**Version:** 1.0 (2026-06-03)

---

## THE FUNDAMENTAL RULE

**Do not duplicate truth across files.**

Each document has a specific responsibility. When the same information appears in multiple documents, the system drifts into incoherence — agents read conflicting truth, make conflicting decisions, and the platform degrades.

If you are unsure where information belongs: consult this document.

---

## THE DOCUMENT HIERARCHY

The [YOUR-AI-NAME] ecosystem uses a 6-layer document hierarchy. Documents higher in the hierarchy have more authority, change less frequently, and govern more fundamental behavior.

```
1. SOUL.md          ← constitutional identity + philosophy + governance
2. ARCHITECTURE.md  ← long-term structural truth
3. AGENTS.md        ← operational execution rules
4. MEMORY.md        ← curated institutional intelligence
5. SYSTEM_MAP.md    ← current infrastructure topology
6. CURRENT_STATE.md ← live operational/runtime state
```

Documents near the top (1-3) are constitutions. They change rarely. Breaking rules encoded here is a serious violation.

Documents near the bottom (5-6) are operational. They change frequently. They reflect current reality, not ideals.

---

## DOCUMENT AUTHORITY TABLE

| Document | Owns | Update Frequency | Owner | Applies To |
|---|---|---|---|---|
| `SOUL.md` | Identity, philosophy, constitutional doctrine, anti-patterns, core beliefs | Rarely (evolutionary) | Billy | All agents, all interfaces |
| `ARCHITECTURE.md` | System design, module boundaries, service contracts, data flows | When architecture changes | Billy + Claude Code | All engineers, all agents |
| `AGENTS.md` | Task lifecycle, workflows, commit rules, memory write policy, escalation | When operational rules change | Billy | All agents |
| `MEMORY.md` | Validated engineering lessons, operational truths, known constraints | Curated additions only | context-injector.py + agents | All agents (read-only for most) |
| `SYSTEM_MAP.md` | Current service topology, ports, active connections | Every infrastructure change | Claude Code | All agents (topology reference) |
| `CURRENT_STATE.md` | Active deployments, current failures, session changes, task progress | After every meaningful change | Claude Code | All agents (runtime reference) |

---

## WHAT BELONGS WHERE

### Belongs in SOUL.md

- Core personality and communication style
- Platform mission and business context
- Local-first doctrine
- SSOT (Single Source of Truth) doctrine
- Memory governance philosophy
- Engineering ethics
- Anti-pattern rules (permanently banned behaviors)
- Autonomy boundaries
- Failure philosophy
- Long-term vision

**Does NOT belong in SOUL.md:**
- Current system status → CURRENT_STATE.md
- Specific service ports → SYSTEM_MAP.md
- Task execution procedures → AGENTS.md
- Module-specific implementation → ARCHITECTURE.md

### Belongs in ARCHITECTURE.md

- System service map (intended design)
- Module boundaries and contracts
- Database schema design
- Request flow diagrams
- Memory layer definitions
- Plugin/integration architecture
- Routing architecture principles

**Does NOT belong in ARCHITECTURE.md:**
- Current operational status → CURRENT_STATE.md
- Governance rules → AGENTS.md
- Why we made certain decisions → ADR files in docs/
- Specific deployment commands → Runbooks in docs/runbooks/

### Belongs in AGENTS.md

- Task lifecycle procedures
- Required workflows (worktree, commit, SSOT-first)
- Skill selection rules
- Memory write policies
- Three-strike rule and escalation
- Destructive action protocol
- Multi-agent coordination rules
- OpenClaw-specific operational details

**Does NOT belong in AGENTS.md:**
- Identity and personality → SOUL.md
- Architecture blueprints → ARCHITECTURE.md
- Historical lessons → MEMORY.md
- Current system state → CURRENT_STATE.md

### Belongs in MEMORY.md

- Validated engineering lessons (with source + timestamp)
- Known platform invariants (things that must always be true)
- Critical constraints discovered through operation
- Operational knowledge that survives sessions
- Debugging patterns that worked

**Does NOT belong in MEMORY.md:**
- Raw logs or noisy debugging output
- Transient operational state
- Duplicate knowledge already in SOUL.md or ARCHITECTURE.md
- Aspirational claims not yet validated
- Task-specific notes → .tasks/ entries

### Belongs in SYSTEM_MAP.md

- Current service inventory (ports, hostnames, container names)
- Current tunnel mappings
- Current model configuration
- Current cron job schedule
- Service health status

**Does NOT belong in SYSTEM_MAP.md:**
- Why services are designed this way → ARCHITECTURE.md
- Operational rules → AGENTS.md
- Historical incidents → docs/audits/ or CURRENT_STATE.md

### Belongs in CURRENT_STATE.md

- Latest session changes (what was deployed/fixed/created)
- Active incidents and blockers
- Current task progress
- Current production readiness scores
- Active warnings and known issues
- Temporary workarounds in effect

**Does NOT belong in CURRENT_STATE.md:**
- Permanent architectural truth → ARCHITECTURE.md
- Constitutional philosophy → SOUL.md
- Long-term vision → docs/vision/

---

## ANTI-DUPLICATION RULES

### Rule D1 — One Document Owns Each Truth

If information exists in Document A, it must NOT be restated in Document B — only cross-referenced.

Wrong:
```
# SOUL.md
The VenzariAI Router runs at :4001...

# ARCHITECTURE.md  
The VenzariAI Router runs at :4001...
```

Correct:
```
# SOUL.md
Local-first doctrine: all inference routes through VenzariAI Router (see ARCHITECTURE.md §2.1)

# ARCHITECTURE.md
VenzariAI Router :4001 — [full specification here]
```

### Rule D2 — Cross-Reference, Don't Copy

When Document A needs to mention something owned by Document B, use a cross-reference:
```
See ARCHITECTURE.md §3.1 for the full V8 module structure.
Ref: SOUL.md §3.7 for the full list of banned anti-patterns.
```

### Rule D3 — Ownership Determines Update Target

When something changes:
- Find which document OWNS that truth
- Update ONLY that document (and CURRENT_STATE.md for operational changes)
- Do NOT update the same content in multiple documents

### Rule D4 — Operational State is Ephemeral

CURRENT_STATE.md and MEMORY.md contain time-sensitive information. Do NOT migrate operational state upward into SOUL.md or ARCHITECTURE.md unless it represents a genuine architectural lesson.

---

## DOCUMENT HEALTH AUDIT CHECKLIST

Run this before closing any task that touches constitutional documents:

```bash
# 1. Check for duplicate content
grep -r "liveTurnTimeoutMs" /opt/[YOUR-AI-NAME]-CTO/docs/constitutional/ | wc -l   # should be 1 (SOUL.md only)
grep -r "VenzariAI Router" /opt/[YOUR-AI-NAME]-CTO/docs/constitutional/ | wc -l   # should appear in ARCHITECTURE.md as primary

# 2. Check all constitutional docs exist
ls /opt/[YOUR-AI-NAME]-CTO/docs/constitutional/
# Expected: SOUL.md, ARCHITECTURE.md, AGENTS.md, DOCUMENT-GOVERNANCE.md

# 3. Verify SOUL.md is deployed to OpenClaw workspace
diff /opt/[YOUR-AI-NAME]-CTO/configs/venzari-vps/soul/SOUL.md /home/billy/.openclaw/workspace/SOUL.md

# 4. Check no constitutional doc has stale state
grep -i "TODO\|FIXME\|PLACEHOLDER\|TBD" /opt/[YOUR-AI-NAME]-CTO/docs/constitutional/*.md
```

---

## CANONICAL FILE PATHS

| Document | Canonical SSOT Path | OpenClaw Deploy Path |
|---|---|---|
| SOUL.md | `/opt/[YOUR-AI-NAME]-CTO/docs/constitutional/SOUL.md` | `/home/billy/.openclaw/workspace/SOUL.md` |
| AGENTS.md | `/opt/[YOUR-AI-NAME]-CTO/docs/constitutional/AGENTS.md` | `/home/billy/.openclaw/workspace/AGENTS.md` |
| ARCHITECTURE.md | `/opt/[YOUR-AI-NAME]-CTO/docs/constitutional/ARCHITECTURE.md` | (reference doc — not injected as system prompt) |
| DOCUMENT-GOVERNANCE.md | `/opt/[YOUR-AI-NAME]-CTO/docs/constitutional/DOCUMENT-GOVERNANCE.md` | (reference doc) |
| MEMORY.md | auto-generated by `context-injector.py` | `/home/billy/.openclaw/workspace/MEMORY.md` |
| CURRENT_STATE.md | `/opt/[YOUR-AI-NAME]-CTO/system-map/CURRENT_STATE.md` | (reference doc) |
| SYSTEM_MAP.md | `/opt/[YOUR-AI-NAME]-CTO/system-map/SERVICES_INVENTORY.md` | (reference doc) |

The SSOT path is always in [YOUR-AI-NAME]-CTO. The deploy path is where the file is read at runtime. They are kept in sync by deploy tasks or by direct copy.

---

## SYNC PROTOCOL

When updating SOUL.md or AGENTS.md:

1. Edit the canonical SSOT path: `/opt/[YOUR-AI-NAME]-CTO/docs/constitutional/{file}.md`
2. Commit to [YOUR-AI-NAME]-CTO
3. Copy to OpenClaw deploy path:
   ```bash
   cp /opt/[YOUR-AI-NAME]-CTO/docs/constitutional/SOUL.md /home/billy/.openclaw/workspace/SOUL.md
   cp /opt/[YOUR-AI-NAME]-CTO/docs/constitutional/AGENTS.md /home/billy/.openclaw/workspace/AGENTS.md
   ```
4. Copy to configs path (for VPS templating):
   ```bash
   cp /opt/[YOUR-AI-NAME]-CTO/docs/constitutional/SOUL.md /opt/[YOUR-AI-NAME]-CTO/configs/venzari-vps/soul/SOUL.md
   ```
5. Verify with: `diff /opt/[YOUR-AI-NAME]-CTO/docs/constitutional/SOUL.md /home/billy/.openclaw/workspace/SOUL.md`
6. Update CURRENT_STATE.md with the change

---

## EVOLUTION POLICY

Constitutional documents (SOUL.md, ARCHITECTURE.md, AGENTS.md) require:
- Explicit decision by Billy
- Task created in `.tasks/` with proper DoD
- Diff reviewed before merge
- CURRENT_STATE.md updated with what changed and why

Operational documents (MEMORY.md, CURRENT_STATE.md) are updated continuously by agents. No approval required.

Structural documents (SYSTEM_MAP.md / SERVICES_INVENTORY.md) are updated by Claude Code after any infrastructure change. No approval required, but must be committed immediately.

---

*DOCUMENT-GOVERNANCE.md v1.0 — [Your Company] · 2026-06-03*
