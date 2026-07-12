# Layer 00 — Foundation

**Stability: LOCKED**  
**Domain:** VPS infrastructure, Docker, SSH tunnel, Nginx

---

## What This Layer Controls

- Both VPS machines (Brain: 127.0.0.1, Memory: 158.220.105.107)
- Docker Compose stacks on [your-vps-address]
- SSH tunnel (Brain ↔ Memory, ports 4000/11434/5432)
- Nginx reverse proxy ([your-domain.com], mail.*, /n8n)
- System cron jobs (heal, watchdog, sync, export)
- User sessions and SSH access

## Contacts

- [your-vps-address]
- [your-vps-address]

## Key Config Files

| File | Location | Purpose |
|---|---|---|
| SSH tunnel | `/etc/systemd/system/venzarai-tunnel.service` | VenzariAI Router port forward |
| Nginx main | `/etc/nginx/sites-enabled/[your-domain.com]` | Domain routing |
| OpenClaw compose | (find with `find /home/billy -name docker-compose.yml`) | Agent container |

## Critical Rules

1. Never change OpenClaw network_mode away from `host`
2. Tunnel must have `ServerAliveInterval=10`
3. Nginx changes require `nginx -t` test before reload
4. No external ports open except 22, 80, 443

## Runbooks

- Full diagnosis: `/opt/YOUR-PROJECT/00-foundation/RUNBOOK.md`
- Domain issues: `/opt/YOUR-PROJECT/00-foundation/RUNBOOK.md`

---

## Live Inventory

| Service | VPS | Config Path | Status |
|---|---|---|---|
| jeannebrain-openclaw-v5 | Brain | /home/billy/.openclaw/openclaw.json | UP |
| venzarai-tunnel.service | Brain | /etc/systemd/system/venzarai-tunnel.service | UP |
| ssh-tunnel-watchdog.service | Brain | /etc/systemd/system/ssh-tunnel-watchdog.service | UP |
| jeanne-cto-sync.sh cron | Memory | /opt/YOUR-PROJECT/ops/venzari-vps/scripts/jeanne-cto-sync.sh | Running (every 15 min) |
| Nginx reverse proxy | Memory | /etc/nginx/sites-enabled/[your-domain.com] | UP |

Repo copies of systemd files: `ops/venzari-vps/systemd/`

---

## Layer Dependencies

This layer is the FOUNDATION — all other layers depend on it:

← 01-intelligence depends on: SSH tunnel (VenzariAI Router :4001)
← 02-memory depends on: SSH tunnel (PostgreSQL :5432, ChromaDB :8001)
← 03-workflow depends on: Nginx routing, Docker compose
← 04-ethical depends on: SSH tunnel ([your-vps-address]
← 05-monitoring depends on: SSH tunnel (Grafana :3001)
