# Layer 03 — Workflow

**Stability: FLEXIBLE**  
**Domain:** n8n, Acelle, HubSpot, Content Engine

---

## What This Layer Controls

- n8n workflow automation (:5678) — connects all services
- Acelle email marketing (:8080) — campaigns, lists
- HubSpot sync (via n8n) — contact/deal sync
- ai-content-engine-api (:5001) — AI content generation

## Sync Schedules

- HubSpot → Acelle: hourly
- Acelle → HubSpot: hourly
- Social posting: on approval (n8n cron)

## Runbooks

- Automation issues: `/opt/YOUR-PROJECT/03-workflow/RUNBOOK.md`
- Acelle setup & integration: `/opt/YOUR-PROJECT/03-workflow/ACELLE.md`

---

## Live Inventory

| Service | VPS | Port | Config Path |
|---|---|---|---|
| n8n | Memory | 5678 (internal) | Docker env, credential store |
| Dashboard | Memory | 5002 (internal) | /opt/jeanne-dashboard/ |
| ai-content-engine-api | Memory | 5001 (internal) | /opt/ai-content-engine/.env |
| ai-content-engine-worker | Memory | — | /opt/ai-content-engine/.env |
| acelle_app | Memory | 80 (internal) | /opt/jeanne-email/.env |
| acelle_db | Memory | 3306 (internal) | Docker volume |
| postfix | Memory | 25 (internal) | Docker env |

External access: [your-domain.com] (Dashboard), [your-domain.com]/n8n, [your-domain.com]/email

---

## Layer Dependencies

← 00-foundation: Nginx routing for all external access
← 01-intelligence: VenzariAI Router provides AI to Content Engine
← 02-memory: PostgreSQL stores approval queue, conversation history
→ 04-ethical: content exports feed training pipeline
