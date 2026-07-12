# [YOUR-AI-NAME] Platform — Services Inventory

**VPS:** Single Venzari VPS ([your-vps-ip-2]) — all services consolidated here
**Last Verified:** 2026-07-06 (Kiro S9 — full security audit + fixes. Firewall active. 20 containers UP. Flows verified.)
**Primary Dashboard:** [YOUR-AI-NAME]-DASHBOARD-V8 via nginx + php8.3-fpm ([your-domain.com])
**Reference Repo:** [YOUR-AI-NAME]-DASHBOARD-V6 (`/opt/[YOUR-AI-NAME]-DASHBOARD-V6`) — code examples and patterns for V8. NOT a running service. — artisan serve is DISABLED
**Legacy V5:** Web container REMOVED 2026-06-17. Worker + Redis MUST stay — ai-content-engine Celery depends on them.
**Container count:** 20 Venzari VPS containers (verified 2026-06-18) + systemd services
**Architecture:** Single VPS. No Venzari VPS. No SSH tunnel topology. No multi-VPS architecture.

## ⚠️ REDIS TOPOLOGY — 4 INSTANCES, DO NOT DELETE WITHOUT CHECKING

| Instance | Type | Port | Used By | DB# | Eviction |
|---|---|---|---|---|---|
| **jeanne_redis** (Docker Redis:7) | Docker Redis | localhost:6379 | V8 Laravel cache+queue+session, slack-bot, ai-content-engine | default | auth required (2026-07-06) |
| **jeanne-dashboard-v5-redis-1** | Docker Redis:7 | 6379 internal | ai-content-engine Celery broker (`CELERY_BROKER_URL=redis://jeanne-dashboard-v5-redis-1:6379/2`) | db/2 | — |
| **claude-mem-valkey-1** | Docker Valkey | 6379 internal | claude-mem BullMQ queues (prefix: `claude_mem_37877:`) | default | — |
| **acelle_redis** | Docker Redis:7 | 6379 internal | Acelle email marketing queue (vendor — do not touch) | default | — |

**WHY 4 INSTANCES EXIST:** Each serves a different application. Session D deleted jeanne-dashboard-v5-redis-1 thinking it was unused — this broke ai-content-engine-worker for 12hrs. Do NOT consolidate without migrating consumers first.

## ⚠️ DATABASE TOPOLOGY — ONE POSTGRES, ONE MYSQL, CHROMADB, CLAUDE-MEM

| Instance | Type | Databases | Used By |
|---|---|---|---|
| **jeanne-db** (Docker postgres:15) | PostgreSQL | `venzarai_hub` (V8 dashboard, all services), `claude_mem` (claude-mem, dedicated as of 2026-07-03), `readykit` (V8 Laravel), `ai_content_engine`, `acelle` (legacy orphan) | ALL SERVICES that need PostgreSQL — PRIMARY: venzarai_hub, claude-mem is separate |
| **acelle_db** (Docker mysql:8.0) | MySQL | `acelle` | Acelle email marketing ONLY |
| **chromadb** | ChromaDB v2 | 6 collections (jeanne_memory: 1443 docs, jeanne_sessions: 23 docs) | L3 vector memory. Use `/api/v2/` endpoints (v1 returns 410 DEPRECATED) |
| **claude-mem** | Node.js memory server | — | L3 semantic memory API. Health: `/healthz` on :37877. Writes to its own dedicated `claude_mem` database (`observations`, `teams`, `projects` tables, etc.) |

**Corrected 2026-07-03 (task L0000000005):** this section previously claimed claude-mem used
`venzarai_hub.observations` ("5110+ rows, ACTIVE") — verified live and found FALSE: no
`observations` table exists in `venzarai_hub` at all. claude-mem was actually crash-looping
(`getaddrinfo ENOTFOUND` on a stale hostname, then a schema collision with `venzarai_hub`'s
own unrelated tables) — fixed by giving it a genuinely dedicated `claude_mem` database, which
now has its own real, auto-migrated schema (`observations`, `teams`, `projects`,
`agent_events`, etc. — 12 tables). L3 is healthy now; the previous "L3 IS HEALTHY" claim
in this doc was not verified against live state when written.

## ⚠️ NETWORKING — SINGLE VPS (consolidated 2026-06-20)

**All services are on Venzari VPS [your-vps-ip-2].** No Brain VPS. No SSH tunnel topology for internal services.

| Service | Local Access | Notes |
|---|---|---|
| LiteLLM Router :4001 | `[your-vps-ip]:4001` | systemd `litellm-router.service` (replaced venzarai-router 2026-07-04) |
| ChromaDB :8001 | `[your-vps-ip]:8001` | Docker container `chromadb` |
| Ollama :11434 | `[your-vps-ip]:11434` | Docker container `ollama` (binds localhost only) |
| PostgreSQL :5432 | `[your-vps-ip]:5432` | Docker container `jeanne-db` |
| claude-mem :37877 | `[your-vps-ip]:37877` | Docker container `claude-mem` |
| Piper TTS :5011 | `[your-vps-ip]:5011` | systemd `piper-tts.service` |

Note: Tailscale is installed for Billy's personal remote access — not used for service-to-service communication.

---

## Core AI Stack (verified 2026-07-06, Kiro S7)

**Inference gateway changed 2026-07-04 (ADR-035): LiteLLM replaced VenzariAI Router at :4001.**
VenzariAI Router archived at `/opt/venzarai-router` — stopped, not deleted, restorable.

| Container/Process | Port | Status | Health Command |
|---|---|---|---|
| **litellm-router.service** (systemd) | 0.0.0.0:4001 (DOCKER-USER chain blocks external) | ✅ UP | `curl http://localhost:4001/health/liveliness` |
| **jeannebrain-openclaw-v5** (docker, bridge network) | [your-vps-ip]:18789, [your-vps-ip]:8787 | ✅ UP (healthy) | `curl http://localhost:18789/health/liveliness` |
| **piper-tts** (systemd) | [your-vps-ip]:5011 | ✅ UP | `curl -X POST http://localhost:5011/synthesize -d '{"text":"test"}' -o /dev/null` |
| **jeanne-slack-bot** (docker) | internal | ✅ UP (healthy) | `docker ps --filter name=jeanne-slack-bot` |
| **ollama** (docker) | [your-vps-ip]:11434 | ✅ UP | `curl http://localhost:11434/api/tags` |
| **claude-mem-claude-mem-server-1** (docker) | [your-vps-ip]:37877 | ✅ UP (healthy) | `curl http://localhost:37877/api/health` |
| **claude-mem-claude-mem-worker-1** (docker) | internal | ✅ UP | `docker ps \| grep claude-mem-worker` |
| **jeanne-warmup-monitor** (systemd) | — | ✅ UP | `systemctl status jeanne-warmup-monitor.service` |
| ~~venzarai-router.service~~ | ~~:4001~~ | ❌ ARCHIVED 2026-07-04 (ADR-035, replaced by LiteLLM) | `/opt/venzarai-router` |
| ~~inference-watchdog~~ (systemd) | — | ❌ RETIRED 2026-07-03 (task I0000000080, masked permanently) | — |

**Ollama models (3-model policy, GOLDEN_RULES Rule 5 — SSOT: model_roles.py):**
- `qwen2.5:1.5b-fast` (986 MB) → Router alias: `fast_chat` — ALWAYS WARM (keep_alive=-1)
- `qwen2.5-coder:7b` (4.7 GB) → Router aliases: `jeanne_primary`, `jeanne-primary` — on demand
- `jeanne_primary` fallback policy: keep cloud fallbacks (Billy decision 2026-07-06, I0000000092). Chain: jeanne_primary → jeanne_primary_groq → jeanne_primary_fast_fallback. Cloud only on local failure.
- `nomic-embed-text:latest` (274 MB) → Router aliases: `embed`, `nomic-embed-text` — ALWAYS WARM

**Banned from Ollama:** `phi3:mini`, `llama3.2:latest`, `jeanne-primary:latest`, `qwen3:1.7b`

**Inference routing chain:**
- Telegram → OpenClaw :8787 (webhook) → OpenClaw → LiteLLM :4001 → Ollama
- Dashboard → BrainService.php → OpenClaw :18789 → LiteLLM :4001 → Ollama
- OpenClaw reaches LiteLLM via `host.docker.internal:4001` (bridge network rule)
- Claude Code → api.anthropic.com DIRECTLY — NEVER through LiteLLM (RULE 13)

## Memory Stack

| Container | Port | Memory Limit | Status | Layer | Health Command |
|---|---|---|---|---|---|
| chromadb | [your-vps-ip]:8001 | 512 MB | UP | L3 vector | `curl http://localhost:8001/api/v2/heartbeat` — USE v2 (v1 returns 410) |
| jeanne-db | [your-vps-ip]:5432 | 512 MB | UP | L2 PostgreSQL | `docker exec jeanne-db pg_isready -U readykit` |
| redis-server (systemd) | localhost:6379 | — | UP | L1 V8 cache | `redis-cli ping` |
| jeanne-dashboard-v5-redis-1 | 6379 internal | — | UP | L1 Celery broker | `docker exec jeanne-dashboard-v5-redis-1 redis-cli ping` |
| claude-mem-valkey-1 | 6379 internal | 128 MB | UP | L1 BullMQ | `docker exec claude-mem-valkey-1 redis-cli ping` |
| acelle_redis | 6379 internal | 64 MB | UP | Acelle cache | `docker exec acelle_redis redis-cli ping` |
| claude-mem-claude-mem-server-1 | [your-vps-ip]:37877 | 256 MB | UP healthy | L3 API | `curl http://localhost:37877/api/health` — NOT /healthz |

## Workflow Stack

| Container | Image | Port (Host:Internal) | Network | Status | Health Command |
|---|---|---|---|---|---|
| n8n | n8nio/n8n:latest | [your-vps-ip]:5678→5678 | jeanne_network | Up 33 hrs | curl http://localhost:5678 |
| ai-content-engine-api | docker-api | [your-vps-ip]:5001→5000 | jeanne_network | Up 33 hrs (healthy) | curl http://localhost:5001/health |
| ai-content-engine-worker | docker-worker | — (internal) | jeanne_network | Up 33 hrs | docker ps |

## Dashboard

| Container/Process | Port | Status | Health Command |
|---|---|---|---|
| **nginx** (systemd) | 0.0.0.0:80 + 0.0.0.0:443 | ✅ UP | `curl -I https://[your-domain.com]` |
| **jeanne-dashboard-v8.service** (php artisan serve) | [your-vps-ip]:5010 | ✅ UP — nginx proxies to this | `curl -s -o /dev/null -w '%{http_code}' http://localhost:5010/api/health/liveliness` |
| **php8.3-fpm** (systemd) | socket | ✅ UP | `systemctl status php8.3-fpm.service` |
| **jeanne-dashboard-v8-worker** (systemd) | — | ✅ UP | `systemctl status jeanne-dashboard-v8-worker.service` |
| **jeanne-db** (docker postgres:15) | [your-vps-ip]:5432 | ✅ UP | `docker exec jeanne-db pg_isready -U postgres` |
| **redis-server** (systemd) | [your-vps-ip]:6379 | ✅ UP | `redis-cli ping` |
| ~~jeanne-dashboard-v5-web-1~~ | ~~:5002~~ | ❌ REMOVED 2026-06-17 | — |

## Email Stack

| Container | Image | Port (Host:Internal) | Network | Status | Health Command |
|---|---|---|---|---|---|
| acelle_app | acelle-acelle_app | [your-vps-ip]:8080→80 | acelle_network | Up 33 hrs | curl http://localhost:8080 |
| acelle_db | mysql:8.0 | 3306/33060 (internal) | acelle_network | Up 33 hrs | mysqladmin ping |
| postfix | boky/postfix:latest | [your-vps-ip]:25→25, :587 | host network | Up 33 hrs (healthy) | postfix status |

## Monitoring Stack

| Container | Port | Status | Security | Health Command |
|---|---|---|---|---|
| grafana | [your-vps-ip]:3001 | ✅ UP | internal only ✓ | `curl -s http://localhost:3001/api/health` |
| loki | [your-vps-ip]:3100 | ✅ UP | internal only ✓ | `curl -s http://localhost:3100/ready` |
| promtail | internal | ✅ UP | internal only ✓ | `docker ps \| grep promtail` |
| prometheus | **0.0.0.0:9090** | ✅ UP | ⚠️ PUBLIC — TASK 1883 FIX NEEDED | `curl -s http://localhost:9090/-/healthy` |

⚠️ **PROMETHEUS SECURITY**: Port 9090 bound to 0.0.0.0 — publicly accessible with no auth. Task 1883 will restrict to [your-vps-ip]:9090.

## Systemd Services (platform-relevant, verified 2026-06-23)

| Service | Port | Status | Notes |
|---|---|---|---|
| venzarai-router.service | 0.0.0.0:4001 | ✅ UP | VenzariAI Router jeanne-router.py v4.1 Hybrid |
| jeanne-dashboard-v8.service | [your-vps-ip]:5010 | ✅ UP | Laravel php artisan serve — nginx proxies to it |
| jeanne-dashboard-v8-worker.service | — | ✅ UP | Laravel queue worker |
| piper-tts.service | [your-vps-ip]:5011 | ✅ UP | British female TTS |
| ~~inference-watchdog.service~~ | — | ❌ RETIRED 2026-07-03 | Was: restarted Ollama on failure -- redundant/buggy, see below |
| jeanne-warmup-monitor.service | — | ✅ UP | Ollama model warmup monitor |
| jeanne-webhook.service | — | ✅ UP | Training completion webhook receiver |
| jeanne-memory.service | — | ✅ UP | [Your-AI-Name] memory API |
| nginx.service | 0.0.0.0:80/443 | ✅ UP | Reverse proxy for [your-domain.com] |
| php8.3-fpm.service | socket | ✅ UP | PHP FPM for V8 |
| redis-server.service | [your-vps-ip]:6379 | ✅ UP | Native Redis for V8 Laravel |
| acelle-queue.service | — | ✅ UP | Acelle email queue worker |
| fail2ban.service | — | ✅ UP | Brute-force protection |
| ssh.service | 0.0.0.0:22 | ✅ UP | SSH access |
| ollama.service | — | ❌ DISABLED/FAILED | Replaced by Docker container `ollama` |
| venzarai-router-tunnel.service | SSH tunnel Brain→Memory (TODO: rename) | :11434, :5432, :8001, :37877, :4001, :5011 fwd + :18800 rev | Up | systemctl status venzarai-router-tunnel |
| jeanne-bridge.service | REST API v3.2 (SOUL-COMPACT.md + memory + Ollama, no Groq fallback when warm) | [your-vps-ip]:18800 | Up | curl http://[your-vps-ip]:18800/health (version=3.2.0) |
| jeanne-webhook.service | Training completion webhook receiver | [your-vps-ip]:9000 | Running | systemctl status jeanne-webhook |
| ssh-tunnel-watchdog.service | Python watchdog (circuit breaker) | — | Up | systemctl status ssh-tunnel-watchdog |
| nginx | Reverse proxy (Venzari VPS) | 80/443 | Up | curl https://[your-domain.com] |
| jeanne-bootstrap-check | Health check script (/usr/local/bin) | — | DEPLOYED | bash /usr/local/bin/jeanne-bootstrap-check |
| jeanne-code | Local model fallback CLI (/usr/local/bin) | — | DEPLOYED ✓ TESTED | jeanne-code --help |

**Note:** The context-stripping proxy (:4002) was built (task 0209) and then removed (2026-05-29) after it broke Claude Code authentication. Claude Code now connects directly to api.anthropic.com. See `docs/claude-code-rollback.md`.

---

## Network & DNS Map

```
Internet → Cloudflare → Venzari VPS :443 (Nginx reverse proxy)
                              ↓
                    jeanne_network (primary Docker network)
                    ├── venzarai-router (4000 internal)
                    ├── ollama (11434 host: [your-vps-ip])
                    ├── chromadb (8001 host: [your-vps-ip])
                    ├── postgres (multiple: 5432 internal + host)
                    ├── redis (multiple: 6379 internal for each network)
                    ├── n8n (5678 host: [your-vps-ip])
                    ├── dashboard (5002 host: [your-vps-ip])
                    ├── ai-content-engine-api (5001 host: [your-vps-ip])
                    └── claude-mem-claude-mem-server-1 (37877 public)

                    monitoring_network (isolated)
                    ├── grafana (3001 host: [your-vps-ip])
                    ├── loki (3100 internal)
                    └── promtail (host mount)

                    acelle_network (email)
                    ├── acelle_app (8080 host: [your-vps-ip])
                    ├── acelle_db (3306 internal)
                    └── acelle_redis (6379 internal)

Venzari VPS ([your-vps-ip] — host network mode)
  └── jeannebrain-openclaw-v5 (WebSocket → Telegram)
      └── SSH tunnel to Venzari VPS (for VenzariAI Router @ 4000)
```

---

## Quick Health Check

**Venzari VPS (21 containers):**
```bash
ssh venzari-vps-billy "docker ps --format 'table {{.Names}}\t{{.Status}}' | sort"
```

**Venzari VPS (1 container + services):**
```bash
docker ps | grep openclaw
systemctl status venzarai-tunnel ssh-tunnel-watchdog
```

**Key endpoints (Venzari VPS [your-vps-ip]):**
- Dashboard: http://[your-vps-ip]:5002
- VenzariAI Router: http://[your-vps-ip]:4001 (internal to jeanne_network)
- Ollama: http://[your-vps-ip]:11434
- ChromaDB: http://[your-vps-ip]:8001
- N8N: http://[your-vps-ip]:5678
- Grafana: http://[your-vps-ip]:3001
- AI Content Engine: http://[your-vps-ip]:5001
- Acelle: http://[your-vps-ip]:8080
- Postgres (ReadyKit): [your-vps-ip]:5432
- Claude-Mem Server: 0.0.0.0:37877

---

## GitHub Repo → Service Mapping (Updated 2026-07-06, Kiro S7)

| GitHub Repo | Local Path | Live Service | Sync Status |
|---|---|---|---|
| MEDIA-HAPPI-AI/YOUR-PROJECT | /opt/YOUR-PROJECT | SSOT (not a running service) | ✅ CLEAN — production branch current |
| MEDIA-HAPPI-AI/[YOUR-AI-NAME]-AI-SWITCHER | /opt/venzarai-router | ~~venzarai-router.service~~ → **ARCHIVED 2026-07-04** — replaced by LiteLLM. Code preserved at /opt/venzarai-router, `systemctl start venzarai-router.service` restores if LiteLLM fails | ⚠️ Archived/restorable |
| MEDIA-HAPPI-AI/[YOUR-AI-NAME]-DASHBOARD-V8 | /opt/[YOUR-AI-NAME]-DASHBOARD-V8 | nginx + php-fpm ([your-domain.com]) | check live |
| MEDIA-HAPPI-AI/YOUR-OPENCLAW | /opt/YOUR-OPENCLAW | jeannebrain-openclaw-v5 container | ✅ CLEAN |
| MEDIA-HAPPI-AI/AI-CONTENT-ENGINE | /opt/ai-content-engine | ai-content-engine-api container | check live |
| MEDIA-HAPPI-AI/[YOUR-AI-NAME]-TRAINING | /opt/jeanne-training | Training pipeline (offline/on-demand) | ✅ production branch c22271b |

**System router (inference gateway):**
LiteLLM is the live system router at :4001 (`litellm-router.service`). Config SSOT: `/opt/litellm-proxy/config.yaml` (template: `ops/router/litellm-local-template.yaml`).
[YOUR-AI-NAME]-AI-SWITCHER (VenzariAI Router / jeanne-router.py) is ARCHIVED at `/opt/venzarai-router` — not running.

**Coding agent optional router (separate, not the system router):**
`ops/router/jeanne-router.sh` — shell wrapper for coding agents (claude/aider/codex/kiro) to use when API limits are hit. Activates only with `--[YOUR-AI-NAME]` flag. Does NOT touch LiteLLM or the production inference chain. See `ops/router/[YOUR-AI-NAME]-ROUTER-README.md`.

## Notes

- **No commit-time gates in sibling repos (2026-07-02, task I0000000065):** commit-time
  governance/enforcement lives only in YOUR-PROJECT. A jeanne-aider approval-flag pre-commit hook
  that had been installed directly into 8 sibling repos was removed — see `ops/README.md` and
  `system-map/CURRENT_STATE.md` for detail.
- **The typed-gate task-closing system is now the real enforcement path (2026-07-02, task
  I0000000066):** it never actually blocked anything before this fix (task_manager.py never
  checked its result). Now genuinely enforced for all 16 layers; legacy V4/V5 is a last-resort
  fallback only. This affects `task_manager.py complete` for every layer/service, not any
  running VPS process directly — see `system-map/CURRENT_STATE.md` for detail.
- **Task schema validation fails closed by default (2026-07-02, task I0000000070):**
  `task_manager.py`'s schema gate used to silently let any malformed task through if
  `jsonschema` wasn't installed or the schema file couldn't load. Now fails closed unless
  `PROJECT_SCHEMA_FAIL_OPEN=1` is explicitly set — relevant if any VPS process runs
  `task_manager.py` without `jsonschema` installed in its environment, since task
  creation/validation will now correctly refuse rather than silently accept.
- **Task ID registry counter is now lock-protected (2026-07-03, task I0000000069):**
  `task_numbering.py`'s `next_id()` used to read/increment/write `REGISTRY.json`'s counters
  with zero locking — concurrent task creation on the same VPS could produce duplicate task
  IDs. Now uses the same Redis-backed `task_lock()` infrastructure as task claiming (see
  Multiple Redis instances note below); relevant if multiple agents or automation processes
  create tasks concurrently against this repo.
- **PostgreSQL backups (fixed 2026-07-03, task I0000000072):** daily via
  `/usr/local/bin/backup-postgresql.sh` (cron `0 3 * * *`) to `/opt/backups/postgresql/`
  (30-day/14-file retention), offsite-copied 30 minutes later via
  `/usr/local/bin/offsite-backup.sh` to `jeanne-b2:billy-jeanne-backups/daily/` (Backblaze B2,
  append-only `rclone copy`). Both crons previously referenced a non-durable `/tmp` script and
  a stale local directory respectively — see `docs/runbooks/BACKUPS.md`.
- **Tiered approval gate Rule 1 is now negation-aware (2026-07-03, task I0000000071):**
  `ops/agent/tiered_approval.py`'s `check_golden_rules_violation()` used to flag any
  description mentioning `patch` near `running`/`container` as a GOLDEN_RULES violation with
  no negation handling — a description correctly stating "never patch the running container"
  false-positived and could not be force-approved. Now checks for a negation word within 5
  words before `patch`; real violations still block as before.
- **OpenClaw agent default model is now `jeanne_primary`, not `fast_chat` (fixed 2026-07-03,
  task I0000000073):** `fast_chat` (phi3:mini) has zero tool-calling support in Ollama, but
  OpenClaw's agent always attaches tool definitions, so `fast_chat` could never actually serve
  a real conversation — every real Telegram message since the 2026-06-23 model policy change
  returned a canned "[Your-AI-Name] is warming up" filler reply, masking the real 400 error. Router
  (`/opt/venzarai-router/jeanne-router.py`, repo [YOUR-AI-NAME]-AI-SWITCHER) also fixed: proactive
  tools-aware rerouting, a real `fast_chat`→`jeanne_primary` fallback chain, and 3 further bugs
  in the tool-calling response pipeline (raw JSON leaking as text, a 422 on echoed tool-call
  turns, an arguments-format mismatch between OpenAI and Ollama). Verified end-to-end via real
  Telegram delivery. Full root-cause chain in `system-map/CURRENT_STATE.md`.
- **Stale OpenClaw runtimes archived, 5 dead services masked (2026-07-03, task I0000000051):**
  `.openclaw-production` and `.openclaw-memory-broken` removed (zero live references, tar-backed
  up first). `litellm-standby`, `memory-api`, `jeanne-stack`, `jeanne-heal`, `ollama-monitor`
  systemd units are now `masked` (were `disabled` but not masked — a manual `systemctl start`
  could still have run them).
- **Ollama keep-warm consolidated to one mechanism (2026-07-03, task I0000000075):** was 5
  separate, uncoordinated pingers (2 referencing the BANNED `jeanne-primary:latest` tag),
  causing memory exhaustion and hangs (Ollama logs: "model requires more system memory than
  is currently available, evicting a model to make space", some requests took 100-468s).
  Only `jeanne-keepwarm.sh` (cron, every 2 min, phi3:mini + embed) remains. Ollama container
  now has `mem_limit: 8g` / `memswap_limit: 10g` (was unlimited) and
  `OLLAMA_MAX_LOADED_MODELS=2` (was 3).
- **`inference-watchdog.service` retired (2026-07-03, task I0000000075):** an UNDOCUMENTED
  service (not previously listed anywhere in this file, which is why it took a full
  `systemctl list-units --all` sweep to surface) that pinged `fast_chat` every 60s with a 20s
  timeout and ran `docker restart ollama` after 2 consecutive failures. Its own log proved
  this was the actual source of the "container restarting every 10-15 min" pattern noted
  earlier in this same investigation as unresolved: each restart forces a full model reload
  that isn't finished 60s later, so the next check "fails" too and restarts again —
  self-reinforcing, no backoff. `jeanne-healthcheck.sh` already covers Ollama liveness more
  conservatively (3-min interval, no restart-storm ever observed in its history) and remains
  the sole watchdog for Ollama. `inference-watchdog.service` is stopped, disabled, and masked;
  script archived to `/opt/backups/repo-dedup/retired-scripts/`.
  **Made permanent (2026-07-03, task I0000000080):** formal decision to retire outright
  rather than redesign — the two watchdogs were redundant even before inference-watchdog's
  bugs, and the root causes it existed to catch are separately fixed
  (`I0000000075`/`I0000000077`/`I0000000078`). Confirmed `masked` with no leftover `.wants/`
  symlinks (permanent across reboots). Deleted the live `/opt/ai/inference-watchdog.py` after
  confirming it matched the existing backup; moved the tracked SSOT copy to
  `docs/archive/dead-scripts/inference-watchdog.py.archived-20260703`.
- **`self-healer.py`/`.sh` and `inference-monitor.sh` archived as superseded (2026-07-03,
  task I0000000081):** never scheduled anywhere (no cron/systemd unit), never wired to
  anything, hardcode `ssh venzari-vps-billy` for services now local (pre-single-VPS design).
  `jeanne-healthcheck.sh` covers the critical services; broader multi-service coverage +
  Slack/Telegram escalation is real but untested — not activated. Moved to
  `docs/archive/dead-scripts/{self-healer.py,self-healer.sh,inference-monitor.sh}
  .archived-20260703`.
- **Router v5.1 generic-exception retry-with-backoff reviewed, kept as-is (2026-07-03, task
  I0000000082):** real `journalctl` data over 24h: 71/4,334 requests hit a transient Ollama
  disconnect, 68% recovered via retry, only 23 exhausted all 3 attempts and failed. Retry
  delay (max ~21s) only applies to this small affected minority and stays well under
  OpenClaw's 300s client timeout post-`I0000000078`. No change made.
- **Router `FALLBACK_CHAIN["fast_chat"]` set back to `[]` (2026-07-03, task I0000000075):**
  had briefly been set to `["jeanne_primary"]` earlier the same investigation. `qwen2.5-coder:7b`
  takes ~113s just to load on this CPU-only VPS and then monopolizes Ollama's single compute
  slot (`OLLAMA_NUM_PARALLEL=1`) once loaded — confirmed live via a stuck runner process at
  485-527% CPU that didn't even respond to Ollama's own unload API call. Every `fast_chat`
  timeout was triggering this fallback, which then blocked all other `fast_chat` requests for
  minutes, causing more timeouts and more fallbacks. Per Billy's direction, local models don't
  need a fallback chain for normal operation; removed.
- **2 more duplicate/obsolete config files removed (2026-07-03, task I0000000075 full sweep):**
  `/opt/ollama/docker-compose.yml` and `/opt/jeanne-venzari-vps/ollama/docker-compose.yml` —
  both dead (zero running containers), both would collide with the live `ollama` container
  name and use inconsistent settings if ever started; archived and removed.
  `ops/configs/docker-compose.v8.yml` + `ops/configs/v8-deploy.sh` — described a
  docker-compose deployment for [YOUR-AI-NAME]-DASHBOARD-V8 that was never how it actually runs
  (live V8 is native PHP via `jeanne-dashboard-v8.service`/`-worker.service`, correctly using
  `[your-vps-ip]`); these files had the pre-consolidation multi-VPS Tailscale IP baked in.
  Archived to `docs/archive/dead-configs/`.
- **Tailscale (`tailscaled`) confirmed still needed, kept active (2026-07-03):** verified
  nothing on the VPS depends on it for internal service-to-service communication (the only
  reference was the now-archived stale `docker-compose.v8.yml`); Billy uses it for his own
  remote access to the VPS from personal devices and wants to connect a home computer in the
  future, so the service itself stays enabled — this is a personal-access tool, not part of
  the internal architecture.
- **fast_chat per-model `max_predict` cap added (2026-07-03, task I0000000077):** the actual
  root cause of "OpenClaw/Telegram not responding" that persisted after I0000000075 — no
  per-model output-length cap meant `fast_chat` inherited the global `MAX_PREDICT=2000`, and
  short prompts don't reliably trigger `phi3:mini` to stop early, so it free-ran toward that
  cap (~125s+ at this CPU's measured ~16 tok/s throughput, worse under load — matched
  observed 300-404s hangs/timeouts). Added `"max_predict": 350` for `fast_chat`/`phi3:mini`
  specifically; `jeanne_primary`/external fallbacks unaffected, keep the global 2000 cap.
- **`jeanne-keepwarm.timer` (systemd, every 5 min) is the actual keep-warm mechanism, not
  the `.sh` cron (2026-07-03, task I0000000077):** a 7th keep-warm mechanism missed during
  I0000000075's sweep — runs `/usr/local/bin/jeanne-keepwarm.py`, a smarter version than the
  bash script that checks `/api/ps` before acting and actively un-pins `qwen2.5-coder:7b` if
  ever found pinned (protects `phi3:mini`'s RAM budget). Both wrote to the same log file,
  confirming they were meant as alternatives; kept the Python/systemd version, removed the
  `jeanne-keepwarm.sh` cron entry, archived the script.
- **Router `Config.TIMEOUT` 550s→270s deployed (2026-07-03, task I0000000078):** router's
  internal timeout exceeded OpenClaw's own client timeout (300s), so OpenClaw's client gave
  up first and never saw the router's friendlier error handling. Fix was committed
  (`7eeeab7`, `MEDIA-HAPPI-AI/[YOUR-AI-NAME]-AI-SWITCHER`) but not yet running; deployed via
  `systemctl restart venzarai-router`, confirmed active with the new timeout, `/health/
  liveliness` → HTTP 200.
- **`ops/agent/claude-code-gate.py` evidence-check deadlock closed (2026-07-03, task
  I0000000076):** formally verified the already-live staged-diff evidence path with a new
  regression test (2/2 passing). Real remaining gap documented: `REPO_DIR` hardcoded to
  `/opt/YOUR-PROJECT` means `git diff --cached` doesn't see a worktree's own staged index —
  the new path only reliably works for commits made directly in the main repo.
- **`ops/agent/claude-code-gate.py` `REPO_DIR` hardcoding fixed (2026-07-03, task
  I0000000083):** `REPO_DIR` is now `_repo_dir()`, resolved per call via `PROJECT_CTO_PATH`
  env override then `git rev-parse --show-toplevel` — the gate now correctly validates a
  worktree's own staged changes/tests instead of silently reading `/opt/YOUR-PROJECT`'s.
- **Multiple Redis instances:** Each network (jeanne, acelle) has its own Redis for isolation
- **Port collision prevention:** All host ports are unique; internal-only services share port 6379
- **Promtail:** Log aggregator for Loki (no exposed port, runs as sidecar)
- **Prometheus & Node-Exporter:** Planned Phase 2 deployment for metrics collection
- **VenzariAI Router image:** Custom build (not ghcr.io/berriai)
- **Claude-Mem Server:** Public exposure (0.0.0.0:37877) for external websocket connections
- **Venzari VPS OpenClaw:** Host network mode, WebSocket-only (no REST), tunnels to Venzari VPS for AI model access
