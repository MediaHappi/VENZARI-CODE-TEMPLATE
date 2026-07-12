---
name: "incident-timeline"
description: "Build a timeline for incident post-mortems. Use after any production incident to reconstruct what happened, when, and why. Queries logs from both VPS, correlates with git history, and outputs a structured timeline. Output goes to docs/incidents/YYYY-MM-DD-incident-name.md."
version: "1.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-6
allowed-tools: Bash, Read, Write
---

# Skill: Incident Timeline Builder

---

## Brief

Build structured post-mortem timeline from logs + git history.

**When to use:**
- Immediately after any production incident (while logs are fresh)
- When asked to document what went wrong
- As part of any root-cause analysis

**Key Facts:**

| Item | Value |
|---|---|
| Output path | `docs/incidents/YYYY-MM-DD-<name>.md` |
| Log sources | `/var/log/jeanne/`, docker logs, systemd journal |
| Git history | `git -C /opt/YOUR-PROJECT log --oneline --since=<time>` |

---

## Detail

### Step 1 — Gather logs from incident window

```bash
INCIDENT_START="2026-05-29 16:00"  # adjust
INCIDENT_END="2026-05-29 20:00"    # adjust

echo "=== Venzari VPS systemd journal ==="
journalctl --since="$INCIDENT_START" --until="$INCIDENT_END" -p err..emerg --no-pager | tail -50

echo "=== OpenClaw logs ==="
docker logs jeannebrain-openclaw-v5 --since="$(date -d "$INCIDENT_START" +%Y-%m-%dT%H:%M:%S)" 2>&1 | head -50
```

### Step 2 — Correlate with git commits

```bash
git -C /opt/YOUR-PROJECT log --oneline --since="2 hours before incident" --until="1 hour after incident"
```

### Step 3 — Write timeline doc

```bash
mkdir -p /opt/YOUR-PROJECT/docs/incidents
# Write to docs/incidents/YYYY-MM-DD-incident-name.md
```

Timeline format:
```markdown
# Incident: <name> — YYYY-MM-DD

## Timeline

| Time (UTC) | Event | Source |
|---|---|---|
| HH:MM | First symptom | log/alert |
| HH:MM | Root cause action | git commit / config change |
| HH:MM | Fix applied | task ID |
| HH:MM | Recovery confirmed | curl HTTP 200 |

## Root Cause

## Fix Applied

## Prevention
```

### Step 4 — Commit and link from CURRENT_STATE.md

```bash
cd /opt/YOUR-PROJECT
git add docs/incidents/
git commit -m "incident: post-mortem $(date +%Y-%m-%d)"
git push origin main
```

---

## Reference

### Past incidents documented

- `docs/claude-code-rollback.md` — proxy incident 2026-05-29
- OpenClaw Telegram cascade — 2026-05-27 (in CURRENT_STATE.md)
