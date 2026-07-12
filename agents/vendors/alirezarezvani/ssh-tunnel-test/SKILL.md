---
name: "ssh-tunnel-test"
description: "Comprehensive test of all SSH tunnels between Venzari VPS and Venzari VPS. Use when tunnel issues are suspected or as a diagnostic step. Tests venzarai-router:4001, ollama:11434, and SSH connectivity itself. Reports tunnel state with specific failure diagnosis commands."
version: "1.0"
compatible-roles:
  - infrastructure
min-claude-version: claude-sonnet-4-6
allowed-tools: Bash
---

# Skill: SSH Tunnel Test

---

## Brief

Test all Venzari VPS ↔ Venzari VPS SSH tunnels in one diagnostic pass.

**When to use:**
- After an incident involving tunnel failure
- When VenzariAI Router is not reachable
- Before any deploy that relies on tunnels

**Key Facts:**

| Item | Value |
|---|---|
| venzarai-router tunnel | Brain:4001 ← Memory:4001 (venzarai-tunnel.service) |
| ollama tunnel | Brain:11434 ← Memory:11434 (ollama-tunnel.service) |
| SSH key | id_ed25519_brain_mesh (NEVER id_rsa for billy@) |
| Watchdog | ssh-tunnel-watchdog.service (circuit breaker) |

---

## Detail

### Step 1 — Test SSH connectivity

```bash
ssh -o ConnectTimeout=5 -o BatchMode=yes venzari-vps-billy "echo SSH-OK" && echo "SSH: OK" || echo "SSH: FAIL"
```

### Step 2 — Test VenzariAI Router tunnel (:4001)

```bash
curl -sf --connect-timeout 5 http://127.0.0.1:4001/health/liveliness && echo ":4001 OK" || echo ":4001 FAIL"
```

### Step 3 — Test Ollama tunnel (:11434)

```bash
curl -sf --connect-timeout 5 http://127.0.0.1:11434/api/tags > /dev/null && echo ":11434 OK" || echo ":11434 FAIL"
```

### Step 4 — Check systemd service status

```bash
systemctl status venzarai-tunnel.service --no-pager | head -5
systemctl status ollama-tunnel.service --no-pager | head -5
systemctl status ssh-tunnel-watchdog.service --no-pager | head -5
```

### Step 5 — If tunnel down — diagnose and restart

```bash
# Check if Venzari VPS is reachable at all
ssh -o ConnectTimeout=5 venzari-vps-billy "docker ps | grep -c Up" 2>/dev/null && echo "Venzari VPS up"

# Restart failed tunnel
systemctl restart venzarai-tunnel.service
systemctl restart ollama-tunnel.service

# Wait 5s and retest
sleep 5
curl -sf http://127.0.0.1:4001/health/liveliness && echo "Tunnel recovered"
```

---

## Reference

### Tunnel failure causes (in order of likelihood)

1. Venzari VPS VenzariAI Router container crashed — `ssh venzari-vps-billy "docker ps | grep venzarai-router"`
2. SSH key issue — run `ssh -vv venzari-vps-billy echo ok` to see auth details
3. Network instability — check `journalctl -u venzarai-tunnel.service --tail 20`
4. Port conflict — `ss -tlnp | grep 4000`
