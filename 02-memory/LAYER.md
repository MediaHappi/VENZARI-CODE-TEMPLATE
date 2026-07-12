# Layer 02 — Memory

**Stability: LOCKED**  
**Domain:** ChromaDB, PostgreSQL, Redis, claude-mem, codegraph, institutional history

> **Architecture:** `docs/architecture/MEMORY_ARCHITECTURE.md`  
> **Agent Rules:** `agents/protocols/memory-governance.md`

---

## Five-Layer Memory Architecture

| Layer | Name | Store | Type | Retention |
|---|---|---|---|---|
| 1 | Operational / Runtime | Redis :6379 | Key-value, fast cache | 365 days (LRU) |
| 2 | Structured System | PostgreSQL :5432 | Relational, audited truth | 90d conversations / permanent audit |
| 3 | Semantic Engineering | claude-mem :37877 + ChromaDB :8001 | Vector + semantic search | Permanent (with aging) |
| 4 | Code Intelligence | codegraph `.codegraph/codegraph.db` | AST + symbol graph | Always-fresh (file-watcher) |
| 5 | Institutional Historical | git + `docs/archive/` + `decision-log.md` | Append-only text | Permanent |

**The future problem is not lack of memory. It is memory governance.**  
Do not collapse all memory into one abstraction. Each layer has a distinct purpose, retrieval mechanism, and governance rule.

---

## Privacy Guarantee

No memory leaves the [your-vps-address]

---

## Runbooks

- Memory issues: `02-memory/RUNBOOK.md`
- Full architecture: `docs/architecture/MEMORY_ARCHITECTURE.md`
- Agent access rules: `agents/protocols/memory-governance.md`

---

## Live Inventory

| Service | Layer | VPS | Port | Status |
|---|---|---|---|---|
| Redis | 1 | Memory | 6379 (internal) | Up |
| PostgreSQL (jeanne-dashboard-v8-db-1) | 2 | Memory | 5432 | Up — databases: readykit, n8n_db, ai_content_engine, claude_mem |
| ChromaDB | 3 | Memory | 8001 (host) | Up — collections: jeanne_obs_detail, jeanne_memory, jeanne_obs_index, jeanne_code_symbols |
| claude-mem server | 3 | Memory | 37877 | Up (healthy) — uses shared postgres (claude_mem db) |
| claude-mem worker | 3 | Memory | — | Up — BullMQ consumer |
| codegraph | 4 | Brain + Memory | local binary | Up — index at .codegraph/codegraph.db |
| git history + docs/archive/ | 5 | Both (SSOT in YOUR-PROJECT) | — | Permanent |

ChromaDB API version: v2 (always use `/api/v2/` prefix)

---

## Layer Dependencies

← 00-foundation: SSH tunnel must be UP for [your-vps-address]
← 01-intelligence: VenzariAI Router provides AI to claude-mem worker (generation)  
→ 03-workflow: n8n reads/writes conversation data to PostgreSQL (Layer 2)  
→ 04-ethical: training export pulls from PostgreSQL conversation tables (Layer 2)  
→ agents: codegraph (Layer 4) is queried at every task start — foundational cognitive infrastructure

---

## Implementation Status

| Layer | Status |
|-------|--------|
| 1 — Redis | Operational |
| 2 — PostgreSQL | Operational |
| 3 — claude-mem + ChromaDB | Operational (adapter fixed, endpoints verified) |
| 4 — codegraph | Operational (both VPSs, MCP server active) |
| 5 — Institutional | Operational (git-backed, append-only) |
| Memory governance protocol | Task 0047 — **COMPLETED** 2026-05-27 (80a83fa) |
| ChromaDB collection governance | Task 0048 — **COMPLETED** 2026-05-27 (b45b71a) |
| Context injection at claim | Task 0049 — **COMPLETED** 2026-05-27 (1d183c2) |
| codegraph-first discipline | Task 0050 — **COMPLETED** 2026-05-27 (117c390) |
| Memory aging pipeline | Task 0051 — **COMPLETED** 2026-05-27 (5981d07) |
| Integration test | Task 0052 — **COMPLETED** 2026-05-27 (9d8b503) |
