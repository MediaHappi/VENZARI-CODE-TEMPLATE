# [YOUR-AI-NAME] Engineering Memory — ChromaDB Collection Schemas
**Last updated:** 2026-05-27
**Status:** ACTIVE — defines the two progressive disclosure collections

---

## Overview

[YOUR-AI-NAME]'s engineering memory implements **progressive disclosure** from claude-mem:
- **Layer 1** (always loaded): `jeanne_obs_index` — compact summaries, ~50 tokens each
- **Layer 2** (selective): `jeanne_obs_detail` — full content, ~500 tokens, fetched only when needed

This achieves ~10x token savings vs loading full observations at session start.

Access pattern:
1. Query `jeanne_obs_index` for top-N matches by semantic similarity
2. Expand only top-2 to full detail from `jeanne_obs_detail`
3. Return formatted context to agent

---

## Collection: `jeanne_obs_index`

**Purpose:** Fast semantic search over observation summaries. Always queried at task-claim time.

**ChromaDB host:** `http://127.0.0.1:8001` ([your-vps-address]

### Document format
```
<50-word summary of the observation>
```
Strict 50-word limit. Agents must compress to this limit when writing.

### Metadata fields

| Field | Type | Description | Example |
|---|---|---|---|
| `agent` | string | Agent that wrote this observation | `"infra-agent"` |
| `type` | string | Observation type | `"fix"`, `"decision"`, `"error"`, `"observation"`, `"milestone"` |
| `ts` | string | ISO 8601 UTC timestamp | `"2026-05-27T11:30:00+00:00"` |
| `task_id` | string | Related task ID (optional) | `"0019"` |
| `tags` | string (JSON array) | Topic tags for filtering | `'["venzarai-router", "ollama", "warm-chain"]'` |
| `has_detail` | string | `"true"` if obs_detail entry exists | `"true"` |

Note: ChromaDB metadata values must be strings, integers, or floats — not lists. Tags are stored as a JSON-encoded string.

### Document ID format
```
sha256(<agent><summary><timestamp>)[:12]
```
12-character hex prefix. Collision probability negligible for < 10,000 observations.

---

## Collection: `jeanne_obs_detail`

**Purpose:** Full observation content for selective expansion. Only fetched when an index entry is selected for expansion.

**Same ChromaDB host as obs_index.**

### Document format
```
<full observation — typically 200-2000 tokens>
```
No length limit enforced, but ChromaDB document limits apply (~512KB).

### Metadata fields

| Field | Type | Description |
|---|---|---|
| `obs_index_id` | string | Matching ID in jeanne_obs_index |
| `agent` | string | Agent that wrote this observation |
| `type` | string | Observation type (mirrors obs_index) |
| `ts` | string | ISO 8601 UTC timestamp |
| `task_id` | string | Related task ID (optional) |

### Document ID format
Same as the corresponding `jeanne_obs_index` ID. One-to-one relationship.

---

## Collection: `jeanne_code_symbols`

**Purpose:** Queryable index of Python code symbols (functions, classes, routes) across the YOUR-PROJECT repo. Reduces file-reading and grep tool calls by agents.

See `code_index_schema.md` for full details.

---

## Operational Notes

### ChromaDB access from [your-vps-address]
ChromaDB runs on [your-vps-address]
```bash
ssh -L 8001:localhost:8001 venzari-vps-billy -N -f
```
The tunnel is not yet set up (Phase 1 pending). Until then, `memory_inject.py` and `memory_write.py` gracefully degrade when ChromaDB is unreachable.

### Schema migrations
ChromaDB collections are schema-less. Metadata fields are additive — adding a new field does not require a migration. Renaming a field requires a full collection re-index.

### Collection creation
Collections are created automatically by `memory_write.py` on first write:
```python
col = client.get_or_create_collection("jeanne_obs_index")
```
No manual setup required.

### Privacy
No conversation content from users should be written to `jeanne_obs_detail`. Engineering observations only: what was changed, what broke, what fixed it.
