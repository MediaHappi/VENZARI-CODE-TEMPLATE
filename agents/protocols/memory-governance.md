# Protocol: Memory Governance — Agent Access Rules

**Protocol:** memory-governance  
**Version:** 1.0  
**Last Updated:** 2026-05-27  
**Supersedes:** The implicit "write to claude-mem only" assumption in memory-injection.md  
**Reference:** `docs/architecture/MEMORY_ARCHITECTURE.md`

---

## Purpose

Every agent must know which memory layer to read and write for each situation. This protocol prevents memory collapse, token explosion, and incoherent retrieval.

---

## Quick Reference

| Question / Situation | Memory Layer | Tool |
|----------------------|-------------|------|
| "What calls this function?" | Layer 4 (codegraph) | `codegraph callers <symbol>` |
| "What would break if I change X?" | Layer 4 (codegraph) | `codegraph impact <symbol>` |
| "How does X connect to Y?" | Layer 4 (codegraph) | `codegraph trace <from> <to>` |
| "What happened last time we touched VenzariAI Router?" | Layer 3 (claude-mem) | `claude_mem_adapter.py query "venzarai-router"` |
| "What engineering decision was made about X?" | Layer 3 + 5 | claude-mem search → decision-log.md |
| "Is the OpenClaw container running?" | Layer 2 (PostgreSQL/system) | `docker ps` |
| "Current session token usage?" | Layer 1 (Redis) | redis-cli GET |
| "Why was Gemini banned?" | Layer 5 (decision-log.md) | Read ADR-003 |
| "What does GOLDEN_RULES.md say about X?" | Layer 5 (institutional) | Read GOLDEN_RULES.md |

---

## At Task Claim (MANDATORY)

Every agent claiming a task MUST inject memory context before starting work:

```python
# Step 1 — Layer 4: structural context
# Already done automatically via codegraph MCP tools in session

# Step 2 — Layer 3: semantic engineering context
python3 ops/agent/claude_mem_adapter.py context "<task description>"

# Step 3 — Layer 5: check if any ADR covers this area
grep -i "<domain>" /opt/YOUR-PROJECT/docs/architecture/decision-log.md
grep -i "<domain>" /opt/YOUR-PROJECT/GOLDEN_RULES.md
```

Do NOT load more than 5 memories at claim time. Scoped retrieval only.

---

## At Task Completion (MANDATORY)

Every agent completing a task MUST write at minimum ONE engineering observation:

```python
# Write to Layer 3 (engineering memory)
python3 ops/agent/claude_mem_adapter.py write \
  "<what was done, what was learned, what to watch out for next time>"

# If the task produced an architectural decision:
# Add to Layer 5 — append to docs/architecture/decision-log.md
# Format: Date, Decision (one sentence), Rejected (what wasn't chosen), Why
```

---

## Layer Write Rules

### Layer 1 — Redis
- Written by services automatically (session state, rate limiting)
- Agents: read-only via Redis CLI for debugging
- Never write agent reasoning or observations to Redis

### Layer 2 — PostgreSQL
- Agents: read-only via `data` agent
- Writes happen via service APIs (Dashboard, n8n, AI content engine)
- Never write directly to postgres from agent code

### Layer 3 — Semantic Engineering Memory (claude-mem)
- Write: completed task observations, debugging discoveries, config lessons
- Write: architectural rationale when not formal enough for Layer 5
- Do NOT write: task-scoped intermediate reasoning
- Do NOT write: content already captured in Layer 5 (ADRs)
- Max content per observation: 500 words

### Layer 4 — Code Intelligence (codegraph)
- Read-only for agents (index auto-updates on code changes)
- Never manually edit the .codegraph/ directory
- Re-index if stale: `cd /opt/YOUR-PROJECT && codegraph index`

### Layer 5 — Institutional Memory (docs, git)
- Write ONLY for decisions with permanent architectural impact
- Append-only — never delete past entries
- Each entry must include: Date, Decision, Rejected alternative, Reason
- Committed to git with a clear commit message

---

## Forbidden Patterns

```
❌ NEVER: Write all agent reasoning to claude-mem
❌ NEVER: Use ChromaDB directly for text storage — use claude-mem adapter
❌ NEVER: Read Layer 5 to answer a structural code question (use codegraph)
❌ NEVER: Inject all memories at task start — scoped retrieval only
❌ NEVER: Write the same observation to multiple layers
❌ NEVER: Silently overwrite a past decision — supersede it explicitly
❌ NEVER: Use Layer 1 (Redis) for persistent engineering knowledge
```

---

## Memory Aging

Layer 3 memories older than 6 months that have been superseded should be tagged `[STALE]` in their content when discovered. The memory aging pipeline (Task 0051) will compress and archive them.

---

## Related

- Full specification: `docs/architecture/MEMORY_ARCHITECTURE.md`
- Memory injection at claim: `agents/protocols/memory-injection.md`
- Evidence requirements: `agents/protocols/evidence-contract.md`
- ChromaDB governance: `02-memory/RUNBOOK.md`
