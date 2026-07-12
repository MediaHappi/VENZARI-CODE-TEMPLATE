---
doc_type: runbook
last_updated: 2026-07-06
ssot_status: CURRENT
audience: all-agents
---

# Rollback Procedures

**Last verified:** 2026-05-30 | **Tasks:** 0071, 0248, 0273

This document covers rollback procedures for all [YOUR-AI-NAME] platform components.
See also: `EMERGENCY_ACCESS.md`, `BACKUPS.md`.

---

## Quick Reference

| What broke | Rollback method | Time |
|---|---|---|
| Bad git commit to YOUR-PROJECT | `git revert` | < 2min |
| Bad VenzariAI Router config | Restore from SSOT | < 5min |
| Bad openclaw.json | Restore from backup | < 3min |
| Container won't start | Roll back image via compose | < 10min |
| Ollama model corrupted | Re-pull model | 5-30min |
| Database corruption | Restore from daily backup | 15-60min |
| Full Venzari VPS failure | Restore from Hetzner snapshot | 30-60min |

---

## 1. YOUR-PROJECT Repo Rollback

### Roll back a bad commit
```bash
# View recent commits
git -C /opt/YOUR-PROJECT log --oneline | head -20

# Option A: Revert (safe — creates new commit)
cd /opt/YOUR-PROJECT
git revert <bad-commit-sha> --no-edit
git push origin main

# Option B: Hard reset (destructive — only if not yet pushed)
git reset --hard <last-good-sha>
git push origin main --force  # DANGER: only for local-only commits
```

### Roll back deployed scripts
```bash
# The SSOT script in repo is authoritative
# 1. Find the good version in git
git -C /opt/YOUR-PROJECT show <sha>:ops/venzari-vps/scripts/<script>.sh > /tmp/<script>.sh
# 2. Inspect, then deploy
sudo cp /tmp/<script>.sh /usr/local/bin/<script>.sh
sudo chmod +x /usr/local/bin/<script>.sh
```

---

## 2. VenzariAI Router Config Rollback

```bash
# View SSOT history
git -C /opt/YOUR-PROJECT log --oneline ops/configs/venzari-vps/venzarai-router_config.yaml | head -10

# Restore from SSOT (last known good)
git -C /opt/YOUR-PROJECT show <good-sha>:ops/configs/venzari-vps/venzarai-router_config.yaml > /tmp/venzarai-router_good.yaml

# Inspect, then apply
scp /tmp/venzarai-router_good.yaml venzari-vps-billy:/tmp/venzarai-router_config.yaml
ssh venzari-vps-billy "sudo cp /tmp/venzarai-router_config.yaml /opt/venzarai-router/venzarai-router_config.yaml && docker restart venzarai-router"
sleep 15
curl -s http://127.0.0.1:4001/health/liveliness | grep alive  # verify
```

---

## 3. OpenClaw Config Rollback

**WARNING: Do not change openclaw.json without verifying Telegram after — CURRENT_STATE.md**

```bash
# Backups are in /home/billy/jeanne-backups/ (daily snapshots)
ls /home/billy/jeanne-backups/openclaw*.json 2>/dev/null | sort | tail -5

# If no local backup, check git history
git -C /opt/YOUR-PROJECT log --oneline configs/venzari-vps/ | head -5

# Restore
cp /home/billy/jeanne-backups/openclaw.<YYYYMMDD>.json /home/billy/.openclaw/openclaw.json
docker restart jeannebrain-openclaw-v5
sleep 15
# Verify Telegram still works (send test message, wait for response)
send-telegram "🔁 OpenClaw rollback test $(date '+%H:%M')"
```

---

## 4. Docker Container Rollback

### Rollback to previous container image
```bash
# On Venzari VPS — check available images
ssh venzari-vps-billy "docker images | grep <service>"

# Rollback by pinning to previous image tag in docker-compose.yml
# Edit: image: <service>:latest → image: <service>:<previous-tag>
# Then rebuild/up

# For containers without versioned tags (use git history)
git -C /opt/YOUR-PROJECT log --oneline configs/venzari-vps/ | head -5
git -C /opt/YOUR-PROJECT show <sha>:configs/venzari-vps/<service>/docker-compose.yml > /tmp/compose_good.yml
ssh venzari-vps-billy "sudo docker-compose -f /path/docker-compose.yml down && sudo docker-compose -f /tmp/compose_good.yml up -d"
```

### Emergency container restart order (Venzari VPS)
```bash
ssh venzari-vps-billy "
docker start ollama        && sleep 15
docker start venzarai-router       && sleep 10
docker start chromadb      && sleep 5
docker-compose -f /home/billy/jeanne-dashboard-v8/docker-compose.yml up -d
"
# Verify
curl -s http://127.0.0.1:4001/health/liveliness | grep alive
```

---

## 5. Ollama Model Rollback

```bash
# If a model is corrupted or wrong:
ssh venzari-vps-billy "ollama rm <model-name>"

# Re-pull
ssh venzari-vps-billy "ollama pull <model-name>"

# Verify
ssh venzari-vps-billy "ollama list | grep <model-name>"

# For jeanne-primary (4.7GB) — takes ~5min
ssh venzari-vps-billy "ollama pull jeanne-primary:latest"
```

---

## 6. PostgreSQL Database Rollback

```bash
# Local backups on Venzari VPS
ssh venzari-vps-billy "ls /home/billy/jeanne-backups/postgres_*.sql.gz 2>/dev/null | sort | tail -5"

# Restore PostgreSQL from backup (to temp DB for verification first)
ssh venzari-vps-billy "
  BACKUP=\$(ls /home/billy/jeanne-backups/postgres_*.sql.gz | sort | tail -1)
  echo \"Restoring from: \$BACKUP\"
  
  # Create temp DB for verification
  docker exec jeanne-dashboard-v8-db-1 psql -U jeanne -c 'CREATE DATABASE jeanne_restore_test;' 2>/dev/null
  
  # Restore to temp DB
  gunzip -c \$BACKUP | docker exec -i jeanne-dashboard-v8-db-1 psql -U jeanne -d jeanne_restore_test
  
  # Verify data
  docker exec jeanne-dashboard-v8-db-1 psql -U jeanne -d jeanne_restore_test -c 'SELECT COUNT(*) FROM information_schema.tables;'
  
  # If verified, drop temp DB
  docker exec jeanne-dashboard-v8-db-1 psql -U jeanne -c 'DROP DATABASE jeanne_restore_test;'
"
```

---

## 7. ChromaDB Vector Store Rollback

```bash
# Backups: /home/billy/jeanne-backups/chroma_backup_YYYYMMDD.tar.gz
ssh venzari-vps-billy "ls /home/billy/jeanne-backups/chroma_backup_*.tar.gz | sort | tail -5"

# Restore ChromaDB from backup
ssh venzari-vps-billy "
  BACKUP=\$(ls /home/billy/jeanne-backups/chroma_backup_*.tar.gz | sort | tail -1)
  echo \"Restoring from: \$BACKUP\"
  
  # Stop ChromaDB
  docker stop chromadb
  
  # Backup current (safety)
  cp -r /opt/chromadb-data /opt/chromadb-data.pre-rollback
  
  # Restore
  rm -rf /opt/chromadb-data/*
  tar -xzf \$BACKUP -C / 
  
  # Restart ChromaDB
  docker start chromadb
  sleep 5
  
  # Verify
  curl -s http://localhost:8001/api/v2/heartbeat
"
```

---

## 8. SSH Tunnel Rollback

```bash
# If venzarai-tunnel is broken
sudo systemctl status venzarai-tunnel.service
sudo journalctl -u venzarai-tunnel.service --tail 20

# Restart
sudo systemctl restart venzarai-tunnel.service
sleep 5
curl -s http://127.0.0.1:4001/health/liveliness | grep alive  # must be "alive"

# If systemd service config is bad, restore from SSOT
git -C /opt/YOUR-PROJECT show HEAD:configs/venzari-vps/venzarai-tunnel.service
```

---

## 9. Full VPS Rollback (Nuclear Option)

If a Venzari VPS is completely unresponsive:
1. Log into Hetzner Cloud Console: https://console.hetzner.cloud
2. Select the server → **Snapshots** tab
3. Choose the most recent snapshot
4. Click **Restore** — this replaces the entire disk
5. After restore, re-run `jeanne-cto-sync.sh` to get latest SSOT

**Before restoring from snapshot, always try:**
- Hetzner rescue console SSH
- `sudo reboot` from web console
- Check disk full: `df -h /`

---

## 10. Claude Code Rollback (If Proxy Setup Returns)

**Trigger:** Claude Code fails to authenticate, shows `Auth conflict` or `Invalid authentication credentials`, or `claude login` hangs.

**Full incident reference:** `docs/claude-code-rollback.md` — this is the complete playbook from the 2026-05-29 incident.

**Quick clean-up steps:**

```bash
# 1. Stop and remove any proxy service
sudo systemctl stop claude-venzarai-router-proxy.service 2>/dev/null
sudo systemctl disable claude-venzarai-router-proxy.service 2>/dev/null
sudo rm -f /etc/systemd/system/claude-venzarai-router-proxy.service
sudo systemctl daemon-reload

# 2. Remove ANTHROPIC overrides from /etc/environment
sudo sed -i '/ANTHROPIC_API_KEY/d' /etc/environment
sudo sed -i '/ANTHROPIC_BASE_URL/d' /etc/environment

# 3. Remove any profile script that sets ANTHROPIC vars
sudo rm -f /etc/profile.d/jeanne-claude.sh

# 4. Kill any running proxy process
pkill -f "claude-venzarai-router-proxy" 2>/dev/null

# 5. Remove shell functions from current session
unset -f claude-use-local claude-use-claude claude-status _jeanne_claude 2>/dev/null
unset ANTHROPIC_API_KEY ANTHROPIC_BASE_URL 2>/dev/null

# 6. Re-authenticate
exec bash  # start clean shell
claude login  # browser OAuth flow
```

**Verify clean state:**
```bash
pgrep -f "claude-venzarai-router-proxy" && echo "BAD: proxy" || echo "OK"
env | grep "^ANTHROPIC" && echo "BAD: env overrides" || echo "OK"
type claude | grep -q "function" && echo "BAD: wrapped" || echo "OK: binary"
```

---

## Verification After Any Rollback

```bash
# Claude Code clean state (7 checks)
pgrep -f "claude-venzarai-router-proxy" && echo "FAIL" || echo "OK: no proxy"
env | grep "^ANTHROPIC" && echo "FAIL" || echo "OK: no env overrides"
type claude | grep -q "function" && echo "FAIL" || echo "OK: binary"
curl -s http://127.0.0.1:4001/health/liveliness | grep -q alive && echo "OK: VenzariAI Router" || echo "FAIL: VenzariAI Router"
docker ps --filter name=jeannebrain-openclaw-v5 --format "{{.Status}}" | grep -q "Up" && echo "OK: OpenClaw" || echo "FAIL: OpenClaw"
ssh venzari-vps-billy "docker exec jeanne-dashboard-v8-redis-1 redis-cli ping" 2>/dev/null && echo "OK: Redis"
curl -sf http://127.0.0.1:37877/healthz > /dev/null && echo "OK: claude-mem" || echo "FAIL: claude-mem"
```
