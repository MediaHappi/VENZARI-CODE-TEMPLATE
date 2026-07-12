# Layer 02 — Memory Runbook

**Last updated:** 2026-05-30 10:30 UTC
**Layer stability:** LOCKED
**Domain:** ChromaDB, PostgreSQL, Redis, claude-mem, conversation export, backup/restore

**Backup status (2026-05-30):** Daily PostgreSQL backup to Backblaze B2 + Cloudflare R2. Weekly full backup (PostgreSQL + ChromaDB + config). Scripts at `/usr/local/bin/backup-lifecycle.sh` and `r2-upload.sh` on [your-vps-address]

Full 5-layer architecture: `docs/architecture/MEMORY_ARCHITECTURE.md`  
Agent rules: `agents/protocols/memory-governance.md`

---

## 5-Layer Memory Overview

| # | Layer | Store | Container/Path | Port | Type | Retention |
|---|---|---|---|---|---|---|
| L1 | Runtime | Redis | `jeanne-dashboard-v8-redis-1` | internal | Fast cache / session | 365 days |
| L2 | Structured Truth | PostgreSQL | `jeanne-dashboard-v8-db-1` | 127.0.0.1:5432 | System config + history | 90 days (conv) |
| L3 | Semantic Memory | ChromaDB + claude-mem | `chromadb` + `claude-mem-server-1` | 8001, 37877 | Vector embeddings + obs | Permanent |
| L4 | Code Intelligence | codegraph | local binary + SQLite | n/a | AST symbol graph | Auto (file watcher) |
| L5 | Institutional | git + docs/archive/ | `/opt/YOUR-PROJECT` | n/a | ADRs, decisions, runbooks | Permanent |

**Privacy guarantee:** No memory leaves the [your-vps-address]

---

## Layer 3: ChromaDB Collection Governance

Audited: 2026-05-28. ChromaDB v0.6.x — use **v2 API only** (v1 deprecated, returns 404).

### Collections (live audit)

| Collection | Documents | Dimensions | Space | Status | Metadata keys |
|---|---|---|---|---|---|
| `jeanne_memory` | 44 | 768 | cosine | **ACTIVE** | session, type, ts, source |
| `jeanne_code_symbols` | 35 | 384 | l2 | **DEPRECATED** (→ codegraph L4) | file, line, name, docstring, type, indexed_at |
| `jeanne_obs_detail` | 0 | — | l2 | reserved (obs detail level) | — |
| `jeanne_obs_index` | 0 | — | l2 | reserved (obs index level) | — |

### Collection: jeanne_memory (ACTIVE — Layer 3 primary)

**Purpose:** General semantic memory. Used by claude-mem server as its primary store.  
**Embedding model:** nomic-embed-text (768d, cosine similarity)  
**Retention:** Permanent. Age out via `ops/venzari-vps/cron/memory-aging.sh` (task 0051).  
**Write path:** claude-mem server API (`POST /v1/memories` on :37877)  
**Query path:** `ops/agent/claude_mem_adapter.py context <task>` or `chromadb_adapter.py search <term>`

### Collection: jeanne_code_symbols (DEPRECATED)

**ADR-009 decision (2026-05-28):** This collection is **superseded by codegraph (Layer 4)**.  
- codegraph uses tree-sitter AST (exact structure) vs chromadb (approximate semantic similarity)
- codegraph has sub-millisecond SQLite reads + full call graph + impact analysis
- jeanne_code_symbols has only 35 docs with no active write path
- **Do not write new entries to this collection.** Reads are safe but unnecessary.
- **Do not delete** — preserved for historical reference.

### ChromaDB API (v2 — use ONLY these)

```bash
# Health / tenants
ssh venzari-vps-billy "curl -s http://127.0.0.1:8001/api/v2/tenants"

# List collections
ssh venzari-vps-billy "curl -s 'http://127.0.0.1:8001/api/v2/tenants/default_tenant/databases/default_database/collections'"

# Count documents in jeanne_memory
ssh venzari-vps-billy "curl -s 'http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/3b99c688-3a4d-4d71-9693-96d3c506bf5f/count'"

# Query jeanne_memory (semantic search, returns top 5)
ssh venzari-vps-billy "curl -s -X POST 'http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/3b99c688-3a4d-4d71-9693-96d3c506bf5f/query' \
  -H 'Content-Type: application/json' \
  -d '{\"query_texts\":[\"inference routing fallback\"],\"n_results\":5}'"
```

### ChromaDB Collection UUIDs (stable)

| Collection | UUID |
|---|---|
| `jeanne_memory` | `3b99c688-3a4d-4d71-9693-96d3c506bf5f` |
| `jeanne_code_symbols` | `da75eaba-5ceb-42f6-922f-aa5fe3472207` |
| `jeanne_obs_detail` | `26ddc80a-e182-4613-a52c-b018a93f2c35` |
| `jeanne_obs_index` | `c0deaf81-95a4-44f1-819c-7945a1f9721b` |

### Retention rules

| Collection | Retain | Age-out trigger |
|---|---|---|
| jeanne_memory | Permanent | Observations > 6 months → aging pipeline (task 0051) |
| jeanne_code_symbols | Permanent (read-only archive) | Never — superseded by codegraph |
| jeanne_obs_detail | As needed | Not yet in use |
| jeanne_obs_index | As needed | Not yet in use |

### Restart ChromaDB
```bash
ssh venzari-vps-billy "docker restart chromadb && sleep 3 && curl -s 'http://127.0.0.1:8001/api/v2/tenants'"
```

### Check ChromaDB logs
```bash
ssh venzari-vps-billy "docker logs chromadb --tail 30"
```

---

## PostgreSQL

### Health check
```bash
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-db-1 pg_isready -U postgres && echo 'POSTGRES OK'"
```

### Connect interactively
```bash
ssh venzari-vps-billy "docker exec -it jeanne-dashboard-v8-db-1 psql -U postgres"
```

### List databases
```bash
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-db-1 psql -U postgres -l"
```

### Check row counts (conversation health)
```bash
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-db-1 psql -U postgres -c 'SELECT COUNT(*) FROM messages;' 2>/dev/null || echo 'table name may differ'"
```

### Restart PostgreSQL
```bash
ssh venzari-vps-billy "cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8 && docker compose restart db"
```

---

## Redis

### Health check
```bash
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-redis-1 redis-cli ping"
# Expected: PONG
```

### Check key count
```bash
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-redis-1 redis-cli DBSIZE"
```

### Restart Redis
```bash
ssh venzari-vps-billy "cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8 && docker compose restart redis"
```

### Flush cache (only if data is stale/corrupted — non-reversible)
```bash
# Ask Billy before running this
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-redis-1 redis-cli FLUSHALL"
```

---

## Backup Procedures

### Backup location
All backups written to: `/home/billy/jeanne-backups/` on [your-vps-address]
Retention: last 30 days.

### Manual PostgreSQL backup
```bash
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-db-1 pg_dump -U postgres jeanne | gzip > /home/billy/jeanne-backups/postgres-manual-\$(date +%Y%m%d-%H%M%S).sql.gz"
```

### Check backup schedule (automated)
```bash
ssh venzari-vps-billy "crontab -l | grep -E 'backup|dump'"
# Expect: daily 2am jeanne-backup.sh, daily 3am PostgreSQL dump, daily 4am Acelle MySQL
```

### Restore PostgreSQL from backup
```bash
# List available backups:
ssh venzari-vps-billy "ls -lt /home/billy/jeanne-backups/*.sql.gz | head -5"
# Restore (stops dashboard web first):
ssh venzari-vps-billy "
  cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8 && docker compose stop web worker
  gunzip -c /home/billy/jeanne-backups/BACKUP_FILE.sql.gz | docker exec -i jeanne-dashboard-v8-db-1 psql -U postgres jeanne
  docker compose start web worker
"
```

---

## Connection Strings

These are only accessible from within the [your-vps-address]

| Service | Connection | Network |
|---|---|---|
| PostgreSQL | `postgresql://postgres:PASSWORD@127.0.0.1:5432/jeanne` | dashboard_net |
| Redis | `redis://127.0.0.1:6379/0` (internal to dashboard stack) | dashboard_net |
| ChromaDB | `http://127.0.0.1:8001` | bridge |

Credentials are in `/opt/[YOUR-AI-NAME]-DASHBOARD-V8/.env` on [your-vps-address]

---

## Common Failures

### Failure: ChromaDB returns 503 / connection refused

```bash
ssh venzari-vps-billy "docker ps | grep chromadb"
# If stopped:
ssh venzari-vps-billy "docker start chromadb"
sleep 3
ssh venzari-vps-billy "curl -s http://127.0.0.1:8001/api/v2/tenants"
```

### Failure: PostgreSQL "too many connections"

```bash
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-db-1 psql -U postgres -c 'SELECT count(*) FROM pg_stat_activity;'"
# Restart web/worker to release connections:
ssh venzari-vps-billy "cd /opt/[YOUR-AI-NAME]-DASHBOARD-V8 && docker compose restart web worker"
```

### Failure: Redis out of memory

```bash
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-redis-1 redis-cli INFO memory | grep used_memory_human"
# Check maxmemory policy:
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-redis-1 redis-cli CONFIG GET maxmemory-policy"
```

### Failure: [your-vps-address]

```bash
ssh venzari-vps-billy "free -h"
# Target: > 2GB free at all times
# If low: check if jeanne-primary-coder:7b is loaded in Ollama (it uses 4.7GB)
ssh venzari-vps-billy "curl -s http://127.0.0.1:11434/api/ps"
# Unload coder model if loaded:
ssh venzari-vps-billy "curl -X POST http://127.0.0.1:11434/api/generate -d '{\"model\":\"jeanne-primary-coder:7b\",\"keep_alive\":0}'"
```

---

## HuggingFace Conversation Export

Daily cron ([your-vps-address]
- **Dataset:** `billy/jeanne-conversations` (private)
- **Format:** JSONL with fields: timestamp, session_id, user_message, jeanne_response, model_used
- **Script:** `/opt/YOUR-PROJECT/ops/venzari-vps/scripts/jeanne-session-cleanup.sh` triggers export
- **Fine-tuning dataset:** `billy/jeanne-finetuned-models` — curated pairs with quality filter

---

## Ollama Configuration

Ollama on [your-vps-address]

| Variable | Value | Purpose |
|---|---|---|
| OLLAMA_KEEP_ALIVE | 30m | Keep model in VRAM for 30 minutes after last use |
| OLLAMA_MAX_LOADED_MODELS | 2 | Allow jeanne-primary + embed model simultaneously |
| OLLAMA_NUM_PARALLEL | 1 | Single request at a time (RAM constrained) |

Warm model: `jeanne-primary:latest` (4.7 GB) — always loaded for OpenClaw inference.
Embed model: `nomic-embed-text` (274 MB) — always loaded for memory tagging.
NOTE: Single-model policy (2026-05-30). Only jeanne-primary:latest + nomic-embed-text. No third model. No jeanne-chat. No qwen2.5:3b orphan tags.

---

## GitHub-First Principle (Rule 16)

Before building any new script, service, or feature in this layer: **search GitHub for existing implementations.**

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load github-search
# Then follow agents/skills/github-search/SKILL.md protocol
```

Copy code structure in most cases. Security audit before committing:
```bash
bash /opt/YOUR-PROJECT/ops/security/github-import-audit.sh /tmp/<cloned-repo>
```

