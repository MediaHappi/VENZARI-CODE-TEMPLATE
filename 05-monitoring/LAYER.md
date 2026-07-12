# Layer 05 — Monitoring

**Stability: FLEXIBLE**  
**Domain:** Grafana, Loki, Promtail, backups, security

---

## Stack

- Promtail → Loki → Grafana (logs + metrics)
- PostgreSQL dump: daily 3 AM
- ChromaDB backup: weekly
- Acelle MySQL: daily 4 AM

## Alerts

| Condition | Threshold | Action |
|---|---|---|
| Response time | > 5s for 5 min | Telegram alert |
| Error rate | > 5% for 10 min | Critical alert |
| Disk | > 80% | Warning |
| SSH tunnel | Down > 60s | Critical + systemd restart |

## Access

Grafana: `ssh -L 3001:127.0.0.1:3001 billy@158.220.105.107` → http://localhost:3001

## Runbooks

- Observability: `/opt/YOUR-PROJECT/05-monitoring/RUNBOOK.md`

---

## Live Inventory

| Service | VPS | Port | Config Path |
|---|---|---|---|
| Grafana | Memory | 3001 (internal) | Docker volume: grafana_data |
| Prometheus | Memory | 9090 (internal) | Docker volume: prometheus_data |
| Loki | Memory | 3100 (internal) | Docker volume |
| node-exporter | Memory | 9100 (internal) | — |

Access Grafana: SSH tunnel to [your-vps-address]
Dashboards: Agent Performance, Training Pipeline, Infrastructure, Memory Layer, Acelle/HubSpot

---

## Layer Dependencies

← 00-foundation: reads from all services via node-exporter + Docker stats
← 01-intelligence: VenzariAI Router metrics scraped by Prometheus
← 02-memory: PostgreSQL + Redis metrics
→ All layers: Grafana alerts route to Telegram via n8n
