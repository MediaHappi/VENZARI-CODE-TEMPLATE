---
name: "container-health-matrix"
description: "Check health of all containers on both Venzari VPS and Venzari VPS in one pass. Use before major deploys, after incidents, or for routine health checks. Outputs a status matrix showing each container's state, uptime, and port bindings. Adapted from alirezarezvani/claude-skills."
version: "1.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-6
allowed-tools: Bash
---

# Skill: Container Health Matrix

---

## Brief

Full container health check across both VPS in one diagnostic pass.

**When to use:**
- Before any major deploy
- After a service incident to assess blast radius
- Routine health check (used by smoke-test.sh)

**Key Facts:**

| Item | Value |
|---|---|
| Venzari VPS | 127.0.0.1 — docker ps direct |
| Venzari VPS | 158.220.105.107 — via ssh venzari-vps-billy |
| Expected containers | 1 Venzari VPS + 15+ Venzari VPS |

---

## Detail

### Step 1 — Venzari VPS containers

```bash
echo "=== Venzari VPS ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
```

### Step 2 — Venzari VPS containers

```bash
echo "=== Venzari VPS ==="
ssh venzari-vps-billy "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>/dev/null
```

### Step 3 — Flag any unhealthy containers

```bash
# Flag containers not in "Up" state
echo "=== UNHEALTHY ==="
docker ps --format "{{.Names}} {{.Status}}" | grep -v "^.*Up " || echo "Venzari VPS: all healthy"
ssh venzari-vps-billy "docker ps --format '{{.Names}} {{.Status}}' | grep -v '^.*Up '" 2>/dev/null || echo "Venzari VPS: all healthy"
```

---

## Reference

### Critical containers (must always be Up)

| Container | VPS | Impact if down |
|---|---|---|
| jeannebrain-openclaw-v5 | Brain | Telegram completely down |
| ollama | Memory | All inference down |
| venzarai-router | Memory | OpenClaw cannot route |
| jeanne-dashboard-v8-web-1 | Memory | Dashboard inaccessible |
