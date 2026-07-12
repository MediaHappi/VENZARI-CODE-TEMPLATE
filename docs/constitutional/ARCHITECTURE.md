# ARCHITECTURE.md — Canonical Structural Blueprint
## [Your Company] · [Your Product]

**Document Class:** Constitutional (Layer 2 — long-term structural truth)  
**Update Frequency:** Only during intentional architectural evolution  
**Authority:** [Your Name] ([your-email])  
**Applies To:** All engineers, all agents, all services  
**Version:** 1.1 (2026-06-03 → updated)

This document is the long-term structural blueprint. It describes the INTENDED DESIGN of the platform — not runtime state (→ CURRENT_STATE.md), not operational rules (→ AGENTS.md), not philosophy (→ SOUL.md).

---

## 1. THE SINGLE BRAIN PRINCIPLE

There is one brain. Everything else is a client.

Telegram, the V8 Dashboard, Claude Code, and Voice are not separate applications. They are entry points — different surfaces on the same persistent intelligence. Every interface reads from and writes to the same memory, the same task system, and the same operational state.

```
┌────────────────────────────────────────────────────────────────┐
│                         INTERFACES                              │
│                                                                 │
│  Telegram    Dashboard      Claude Code     Voice / Future      │
│  (OpenClaw)  (V8 Laravel)   (Venzari VPS)     (Whisper/Piper)    │
└──────┬───────────┬──────────────┬──────────────┬───────────────┘
       │           │              │              │
       └───────────┴──────────────┴──────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                     BRAIN VPS (127.0.0.1)                    │
│                                                                 │
│  OpenClaw container    Nginx reverse proxy    Claude Code CLI   │
│  jeanne-bridge         [YOUR-AI-NAME]-CTO repo        SSH tunnel        │
│                                                                 │
│  Stateless. Disposable. Holds NO models. Holds NO persistent    │
│  data. Can be rebuilt in <10 minutes.                           │
└───────────────────────────┬────────────────────────────────────┘
                            │ SSH tunnel
                            │ :4001 (VenzariAI Router)
                            │ :5003 (jeanne-api)
                            │ :5011 (Piper TTS)
                            │ :11434 (Ollama)
                            │ :5432 (PostgreSQL)
                            │ :8001 (ChromaDB)
                            │ :37877 (claude-mem)
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                  MEMORY VPS (158.220.105.107)                   │
│                                                                 │
│  VenzariAI Router :4001     Ollama :11434                       │
│  jeanne-api :5003           Piper TTS :5011                     │
│  PostgreSQL :5432           ChromaDB :8001                      │
│  claude-mem :37877          Redis :6379                         │
│  V8 Dashboard :5010         n8n :5678                           │
│  Acelle :8080               Grafana :3001                       │
│                                                                 │
│  Stateful. The source of truth for ALL persistent data.         │
└────────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────────┐
│                      [YOUR-AI-NAME]-CTO REPO                            │
│                                                                 │
│  The operational brain. Read by ALL agents. Written by Claude   │
│  Code (primary). The single source of truth for doctrine,       │
│  task queue, system map, and configuration templates.           │
│                                                                 │
│  /opt/[YOUR-AI-NAME]-CTO on both VPSes (synced on session start)        │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. SERVICE ARCHITECTURE

### 2.1 Core Services

| Service | Location | Port | Purpose |
|---|---|---|---|
| VenzariAI Router | Venzari VPS (systemd) | :4001 | Inference gateway — all AI calls route through here |
| Ollama | Venzari VPS (systemd) | :11434 | Local model runtime — jeanne-primary + nomic-embed-text |
| jeanne-api | Venzari VPS (Docker) | :5003 | Python REST API — Telegram bridge, memory queries |
| V8 Dashboard | Venzari VPS (Docker) | :5010 | Laravel+React web UI at [your-domain.com] |
| jeanne-bridge | Venzari VPS (systemd) | :18800 | Inference proxy for V8 Dashboard chat |
| OpenClaw | Venzari VPS (Docker) | host | Telegram agent — `network_mode: host` (mandatory) |
| Piper TTS | Venzari VPS (systemd) | :5011 | Text-to-speech with British voice profile |
| claude-mem | Venzari VPS (Docker) | :37877 | Semantic memory search (ChromaDB) |
| PostgreSQL | Venzari VPS (Docker) | :5432 | Primary database — all persistent structured data |
| Redis | Venzari VPS (Docker) | :6379 | Session cache, rate limiting, hot state |
| ChromaDB | Venzari VPS (Docker) | :8001 | Vector store for L3 semantic memory |
| n8n | Venzari VPS (Docker) | :5678 | Workflow automation |
| Acelle | Venzari VPS (Docker) | :8080 | Email marketing (MySQL) |
| Grafana | Venzari VPS (Docker) | :3001 | Observability (Loki) |

### 2.2 Model Policy

**EXACTLY two models in Ollama. No exceptions.**

| Model | Size | Purpose |
|---|---|---|
| `jeanne-primary:latest` | ~4.7 GB | ALL inference: chat, code, reasoning, analysis |
| `nomic-embed-text:latest` | ~274 MB | ALL embeddings: memory search, semantic retrieval |

Total: ~5 GB. Venzari VPS has ~11 GB RAM. Leaves ~6 GB for OS + all other services.

**Never load a third model.** The two-model policy exists because RAM exhaustion cascades to 500 errors across all services.

### 2.3 Inference Chain

Every AI request flows through this chain:

```
User request
     │
     ▼
Interface (OpenClaw / V8 Dashboard / jeanne-bridge)
     │ builds system prompt: SOUL.md + MEMORY.md + conversation history
     ▼
VenzariAI Router :4001
     │ local-first routing
     ▼ (primary)                    ▼ (fallback — emergency only)
Ollama :11434                   Groq / Mistral / OpenRouter
jeanne-primary:latest             (external APIs — rate limits apply)
     │
     ▼
Response streams back through interface to user
```

**Critical:** OpenClaw accesses the VenzariAI Router via SSH tunnel (Venzari VPS :4001 → Venzari VPS :4001). OpenClaw MUST use `network_mode: host` to reach localhost:4001. Bridge mode breaks this.

---

## 3. V8 DASHBOARD ARCHITECTURE

### 3.1 Stack

- **Backend:** Laravel 11 (PHP 8.2)
- **Frontend:** React + TypeScript + Inertia.js + Vite
- **Database:** PostgreSQL `venzarai_hub` schema
- **Auth:** Sanctum (session-based, not JWT)
- **Deployment:** Docker container on Venzari VPS, port :5010

### 3.2 Module System

Modules are PHP namespaces in `app/Platform/Modules/` — NOT external packages. Each module is self-contained but shares the Laravel container. Zero dependency on nwidart/modules.

```
app/Platform/Modules/{ModuleName}/
    ModuleServiceProvider.php   — registers routes, views, bindings
    Controllers/                — module controllers
    Services/                   — module business logic
    Models/                     — module-specific models
    routes.php                  — module routes
    module.json                 — module manifest (name, slug, enabled, routes_prefix)

resources/js/features/{module-name}/
    index.tsx                   — module entry point
    components/                 — module components
    hooks/                      — module hooks
```

Module registration is automatic — `PlatformServiceProvider` discovers and loads all `ModuleServiceProvider.php` files at boot.

### 3.3 Navigation Groups

The V8 Dashboard is organized into 6 navigation groups (canonical source: `docs/architecture/V8-NAVIGATION-SPEC.md`):

| Group | Pages |
|---|---|
| **INTELLIGENCE** | Dashboard, Memory, Analytics |
| **WORKPLACE** | Chat, Voice, Proposals, Messaging, Email, Clients, Social, Websites, Documents, Uploads, Editor |
| **AI STUDIO** | AI Prompts, AI Creation, AI Templates, AI Author, AI Influencer, AI Code, AI Rewrite, AI Agents, AI Image, AI Reader |
| **OPERATIONS** | Terminal, Conductor, Tasks, Skills, Training |
| **SYSTEM** | Health, Infrastructure, AI Models, AI Routing, Alerts, Operations |
| **ACCOUNT** | Usage, Settings, Notifications, Users, Teams, Billing |

**Route cache rule:** After adding new routes to `routes/web.php`, always run `php artisan route:cache` on Venzari VPS. Failure to do this causes new routes to silently 404 (stale cache incident 2026-06-02).

### 3.4 Database Schema

Primary database: `venzarai_hub` (PostgreSQL)

Key tables:
- `users` — authentication and profiles
- `chat_messages` — conversation history (L2 memory)
- `tasks` — task management
- `documents` — file/output storage
- `ai_templates` — prompt templates
- `subscriptions`, `subscription_plans` — billing
- `audit_logs` — L2 system truth

Acelle email marketing uses its own MySQL database — separate from the main PostgreSQL.

### 3.5 API Design

All API routes follow: `/api/{module}/{action}`

Authentication: Laravel Sanctum session cookies (not Bearer tokens for dashboard — Bearer for external API access)

Response format: JSON with consistent envelope:
```json
{
  "success": true,
  "data": {},
  "message": "optional",
  "errors": {}
}
```

---

## 4. MEMORY ARCHITECTURE

Memory is the platform's most valuable asset. It is layered deliberately — each layer serves a different purpose and has different retention and access patterns.

### 4.1 The Five Memory Layers

| Layer | Store | Purpose | Retention | Answers |
|---|---|---|---|---|
| L1 — In-context | Active conversation window | Current reasoning context | Session only | "What is being discussed?" |
| L2 — Session | PostgreSQL `venzarai_hub` | Conversation history, system audit log | 90 days (conv), permanent (audit) | "What has the system done?" |
| L3 — Semantic | ChromaDB + claude-mem :37877 | Engineering knowledge, debugging history, lessons learned | Permanent (with aging) | "What did we learn?" |
| L4 — Structured | [YOUR-AI-NAME]-CTO docs | Architectural decisions, runbooks, task state, CURRENT_STATE | Permanent | "What is the system's state and design?" |
| L5 — Institutional | Git history + ADRs | Permanent record of why decisions were made | Permanent | "Why does the system work this way?" |

### 4.2 Context Injection Protocol

Every AI conversation must receive:
1. System prompt from SOUL.md (identity + governance)
2. L3 semantic search results from claude-mem (relevant engineering knowledge)
3. MEMORY.md contents (curated operational facts)
4. Recent conversation history (L2 retrieval)

This is the "full context injection" that gives [Your-AI-Name] continuity across sessions.

### 4.3 Memory Governance Rules

- MEMORY.md is curated intelligence, NOT a log file
- Every L3 write should be intentional (validated discovery, not noise)
- L4 and L5 writes are permanent — treat them with the same care as git commits
- Do NOT collapse layers — each layer has a different eviction policy and access pattern
- See `docs/architecture/MEMORY-GOVERNANCE.md` for full governance specification

---

## 5. OPENCLAW ARCHITECTURE

OpenClaw is the Telegram + voice agent. It is a Docker container on Venzari VPS that:
1. Long-polls Telegram for messages
2. Looks up session state in PostgreSQL (via SSH tunnel :5432)
3. Queries L3 memory via context-injector.py → claude-mem :37877
4. Constructs full prompt: SOUL.md + MEMORY.md + conversation history
5. Sends to VenzariAI Router :4001 (SSH tunnel → Venzari VPS)
6. Streams response back to Telegram
7. Stores conversation turn in L2 and L3

**Critical constraints:**
- MUST use `network_mode: host` (accesses localhost SSH tunnel ports)
- `liveTurnTimeoutMs` is BANNED in openclaw.json (causes crash loop)
- Must NOT be proxied through any LiteLLM or intermediate layer (removed 2026-05-30)

---

## 6. ROUTING ARCHITECTURE

### 6.1 Public Traffic

```
Internet → Cloudflare → Nginx (Venzari VPS :80/:443)
             → [your-domain.com] → V8 Dashboard :5010
             → api.[your-domain.com] → jeanne-api :5003
             → (future) → voice endpoint
```

### 6.2 Internal AI Traffic

```
OpenClaw (Venzari VPS host:4001) 
    → SSH tunnel 
    → VenzariAI Router (Venzari VPS :4001)
    → Ollama :11434 (primary)
    → External APIs (Groq/Mistral/OpenRouter — fallback only)

V8 Dashboard (browser) 
    → /api/chat/stream 
    → Laravel ChatController 
    → jeanne-bridge :18800 (Venzari VPS, via reverse SSH tunnel)
    → VenzariAI Router :4001 (Venzari VPS)
    → Ollama :11434
```

### 6.3 Claude Code Traffic

Claude Code connects DIRECTLY to `api.anthropic.com`. No proxy. No intermediary.

**This is enforced by Golden Rule 13 and must never change.**

VenzariAI Router at :4001 is for OpenClaw and V8 Dashboard only. Claude Code has its own OAuth credentials in `~/.claude/.credentials.json`.

---

## 7. PLUGIN AND INTEGRATION ARCHITECTURE

### 7.1 OpenClaw Plugins

OpenClaw skills are defined in `/home/billy/.openclaw/workspace/skills/` — each skill is a JSON definition with:
- `name` — skill identifier
- `description` — what it does (used for intent matching)
- `tools` — array of tool calls to execute
- `triggers` — phrases that activate the skill

Skills are discovered by OpenClaw at boot from the workspace directory.

### 7.2 Claude Code Skills

Claude Code skills live in `agents/skills/{skill-name}/SKILL.md`. Each skill is:
- A markdown document with frontmatter (`name`, `description`)
- A workflow with numbered steps
- Optional scripts in `scripts/` subdirectory

Skills are invoked via the `Skill` tool in Claude Code.

### 7.3 External Integrations

| Integration | Protocol | Use Case |
|---|---|---|
| HubSpot CRM | REST API (hubspot skill) | Contact, deal, note management |
| Telegram | Long-poll bot API | Primary chat interface |
| n8n | Internal REST | Workflow automation |
| Acelle | REST API | Email marketing |
| Google Drive | OAuth + gdrive-ingest.py | Document sync (6am daily) |
| Slack | Bot API (via Slack bot) | Team notifications |
| GitHub | gh CLI + Actions | Repo management, CI/CD |

---

## 8. REPO INTELLIGENCE ARCHITECTURE

The [YOUR-AI-NAME]-CTO repository is the platform's cognitive backbone — not just a config store.

### 8.1 Repository Structure

```
/opt/[YOUR-AI-NAME]-CTO/
├── .tasks/           — task queue (all work tracked here)
├── agents/           — agent skills, personas, catalogs
├── configs/          — service configs (SSOT before deployment)
├── docs/
│   ├── constitutional/ — SOUL.md, AGENTS.md, ARCHITECTURE.md (this file), governance
│   ├── architecture/   — detailed architecture docs (sub-topics)
│   ├── audits/         — operational audit reports
│   ├── governance/     — task drift prevention, memory governance
│   ├── runbooks/       — per-service operational runbooks
│   ├── vision/         — strategic direction documents
│   └── plans/          — implementation plans
├── ops/              — operational scripts (task manager, skill loader, etc.)
├── repo-intelligence/ — reference repos, external knowledge registry
├── system-map/       — CURRENT_STATE.md, VERIFIED-STATE, SERVICES_INVENTORY
└── interfaces/       — interface-specific configs (jeanne-bridge, etc.)
```

### 8.2 Knowledge Flow

Every discovery, fix, and decision must flow back into the repo:

```
Discovery → runs against system
         → if significant: write to L3 (claude-mem)
         → if architectural: write to docs/
         → if operational: update CURRENT_STATE.md
         → if it changes how things work: write ADR
         → always: commit with descriptive message
```

---

## 9. AUTONOMOUS ENGINEERING ARCHITECTURE

The long-term target architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS LAYER                          │
│  Self-repair · Self-improvement · Task orchestration        │
│  (OpenClaw cron sessions + Claude Code scheduled tasks)     │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                   INTELLIGENCE LAYER                         │
│  VenzariAI Router · Ollama · jeanne-bridge                  │
│  claude-mem · ChromaDB · Memory governance                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                    INTERFACE LAYER                           │
│  Telegram (OpenClaw) · V8 Dashboard · Voice · API           │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                        │
│  Venzari VPS · Venzari VPS · SSH tunnels · Docker              │
│  PostgreSQL · Redis · Nginx · Cloudflare                    │
└─────────────────────────────────────────────────────────────┘
```

The autonomous layer does not exist yet in full form. It is the destination. Each task should move the platform closer to it.

---

## 10. CROSS-REFERENCE DOCUMENTS

For detailed coverage of specific areas:

| Topic | Document |
|---|---|
| Full service map with ports | `system-map/SERVICES_INVENTORY.md` |
| Memory layer governance | `docs/architecture/MEMORY-GOVERNANCE.md` |
| V8 module system | `docs/architecture/V8-MODULE-SYSTEM.md` |
| V8 navigation spec | `docs/architecture/V8-NAVIGATION-SPEC.md` |
| VenzariAI Router spec | `docs/architecture/VENZARAI-ROUTER-SPEC.md` |
| Inference chain verification | `docs/AI-CHAIN-VERIFIED.md` |
| Deployment guide | `docs/architecture/V8-DEPLOYMENT-GUIDE.md` |
| Current runtime state | `system-map/CURRENT_STATE.md` |
| Operational agent rules | `docs/constitutional/AGENTS.md` |
| Constitutional identity | `docs/constitutional/SOUL.md` |

---

*ARCHITECTURE.md v1.0 — [Your Company] · 2026-06-03*  
*Synthesized from: UNIFIED-ARCHITECTURE.md, MEMORY-GOVERNANCE.md, V8-MODULE-SYSTEM.md, VENZARAI-ROUTER-SPEC.md, SERVICE-DEPENDENCY-MAP.md, docs/architecture/*
