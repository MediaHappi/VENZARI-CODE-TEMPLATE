---
name: "cron-audit"
description: "Audit all cron jobs on both VPS for conflicts, duplicates, and missing jobs. Use after adding/removing cron jobs or after incidents related to scheduling. Lists all crontabs, checks for duplicates (past cause of Telegram crashes), and verifies expected jobs are present."
version: "1.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-6
allowed-tools: Bash
---

# Skill: Cron Audit

---

## Brief

Audit all cron jobs on Venzari VPS and Venzari VPS.

**When to use:**
- After adding or removing any cron job
- If you suspect a scheduled task is running twice (past Telegram crash cause)
- Weekly maintenance

**Key Facts:**

| Item | Value |
|---|---|
| Past incident | Duplicate crons caused Telegram cascade 2026-05-27 |
| Cron files | `/etc/cron.d/`, user crontabs (`crontab -l`) |

---

## Detail

### Step 1 — Venzari VPS cron jobs

```bash
echo "=== Venzari VPS system crons ==="
ls /etc/cron.d/ && cat /etc/cron.d/jeanne* 2>/dev/null

echo "=== Venzari VPS user crontab ==="
crontab -l 2>/dev/null || echo "no user crontab"
```

### Step 2 — Venzari VPS cron jobs

```bash
echo "=== Venzari VPS system crons ==="
ssh venzari-vps-billy "ls /etc/cron.d/ && cat /etc/cron.d/jeanne* 2>/dev/null"

echo "=== Venzari VPS user crontab ==="
ssh venzari-vps-billy "crontab -l 2>/dev/null || echo 'no user crontab'"
```

### Step 3 — Check for duplicates

```bash
# Flag any identical schedule + command combinations
crontab -l 2>/dev/null | sort | uniq -d | head -5
ssh venzari-vps-billy "crontab -l 2>/dev/null | sort | uniq -d | head -5"
```

### Step 4 — Verify expected jobs exist

Expected jobs (Venzari VPS):
- `*/15 * * * *` — jeanne-cto-sync.sh
- Daily health check script

---

## Reference

### Past incident

2026-05-27: Duplicate morning-brief and evening-summary crons fired simultaneously,
causing OpenClaw session conflicts and Telegram 500 errors. Fix: deduplicated to 9 jobs.
Always check for duplicates before adding new scheduled jobs.
